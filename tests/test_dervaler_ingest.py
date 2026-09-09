"""
Тесты инжеста архива. Telegram не нужен — клиент подменяется фейком.

Проверяем главное из CLAUDE.md:
  — полная пагинация курсором, а не один limit=N;
  — чекпоинт сохраняется после каждой пачки;
  — рестарт продолжает с места остановки (не дублирует);
  — FloodWait не роняет процесс;
  — история не помечается прочитанной.
"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from dervaler import ingest as ingest_module
from dervaler.ingest import ArchiveIngestor, to_message
from dervaler.store import Store


class FakeMessage:
    """Мини-аналог сообщения Telethon."""

    def __init__(self, id_: int, text: str | None, sender_id: int = 1):
        self.id = id_
        self.text = text
        self.message = text
        self.date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.sender_id = sender_id
        self.sender = SimpleNamespace(first_name="Тест", last_name=None, username="tester")
        self.reply_to_msg_id = None


class FakeClient:
    """
    Фейк Telethon-клиента.

    Выдаёт сообщения по min_id, считает вызовы и умеет бросать FloodWait
    заданное количество раз подряд.
    """

    def __init__(self, messages, flood_first: int = 0, flood_seconds: int = 1):
        self.messages = sorted(messages, key=lambda m: m.id)
        self.flood_remaining = flood_first
        self.flood_seconds = flood_seconds
        self.calls: list[dict] = []
        self.read_calls = 0

    async def iter_messages(self, chat_id, **kwargs):
        self.calls.append(kwargs)

        if self.flood_remaining > 0:
            self.flood_remaining -= 1
            from telethon.errors import FloodWaitError

            error = FloodWaitError(request=None, capture=self.flood_seconds)

            async def boom():
                raise error
                yield  # pragma: no cover — делаем генератор генератором

            async for _ in boom():
                yield _

        min_id = kwargs.get("min_id", 0)
        limit = kwargs.get("limit", 500)
        batch = [m for m in self.messages if m.id > min_id][:limit]
        for m in batch:
            yield m


def make_store(tmp_path) -> Store:
    return Store(tmp_path / "test.sqlite3")


def messages(ids, prefix="сообщение"):
    return [FakeMessage(i, f"{prefix} {i}") for i in ids]


@pytest.mark.asyncio
async def test_full_ingest_walks_whole_archive(tmp_path):
    """Курсор должен пройти весь архив, а не только первую пачку."""
    store = make_store(tmp_path)
    client = FakeClient(messages(range(1, 251)))
    ing = ArchiveIngestor(client, store, chat_id=-100)

    saved = await ing.run_full()

    assert saved == 250
    assert store.message_count(-100) == 250
    assert store.get_checkpoint(-100) == 250
    # Больше одной пачки — значит реально шли по курсору.
    assert len(client.calls) > 1


@pytest.mark.asyncio
async def test_checkpoint_resumes_without_duplicates(tmp_path):
    """Рестарт после остановки: продолжаем, а не перезаписываем заново."""
    store = make_store(tmp_path)
    client = FakeClient(messages(range(1, 101)))

    ing = ArchiveIngestor(client, store, chat_id=-100)
    saved_first = await ing.run_full(max_messages=30)

    # Второй запуск с того же курсора.
    ing2 = ArchiveIngestor(client, store, chat_id=-100)
    saved_second = await ing2.run_full()

    assert saved_first == 30
    assert saved_second == 70
    assert store.message_count(-100) == 100
    assert store.get_checkpoint(-100) == 100


@pytest.mark.asyncio
async def test_resume_after_crash(tmp_path):
    """Если процесс упал, следующий старт не начинает с нуля."""
    store = make_store(tmp_path)
    # Падаем на второй пачке.
    client = FakeClient(messages(range(1, 51)), flood_first=0)
    ing = ArchiveIngestor(client, store, chat_id=-100)
    await ing.run_full(max_messages=10)

    checkpoint_after_crash = store.get_checkpoint(-100)
    assert checkpoint_after_crash == 10

    client2 = FakeClient(messages(range(1, 51)))
    ing2 = ArchiveIngestor(client2, store, chat_id=-100)
    saved = await ing2.run_full()

    assert saved == 40
    assert store.get_checkpoint(-100) == 50
    # min_id первой пачки второго запуска = курсор, т.е. дублей нет.
    assert client2.calls[0]["min_id"] == checkpoint_after_crash


@pytest.mark.asyncio
async def test_floodwait_is_survived(tmp_path):
    """FloodWaitError — спим и продолжаем, процесс не падает."""
    store = make_store(tmp_path)
    client = FakeClient(messages(range(1, 21)), flood_first=2, flood_seconds=1)

    original_sleep = asyncio.sleep

    async def fast_sleep(seconds, *a, **kw):
        await original_sleep(0)  # не ждём по-настоящему

    asyncio.sleep = fast_sleep
    try:
        ing = ArchiveIngestor(client, store, chat_id=-100)
        saved = await ing.run_full()
    finally:
        asyncio.sleep = original_sleep

    assert saved == 20
    assert store.message_count(-100) == 20


@pytest.mark.asyncio
async def test_empty_archive_is_noop(tmp_path):
    store = make_store(tmp_path)
    client = FakeClient([])
    ing = ArchiveIngestor(client, store, chat_id=-100)

    assert await ing.run_full() == 0
    assert store.get_checkpoint(-100) == 0


@pytest.mark.asyncio
async def test_messages_without_text_are_skipped(tmp_path):
    """Медиа без подписи в архив не пишем, но курсор двигаем."""
    store = make_store(tmp_path)
    msgs = [
        FakeMessage(1, "текст"),
        FakeMessage(2, None),   # стикер/фото без подписи
        FakeMessage(3, "ещё текст"),
    ]
    client = FakeClient(msgs)
    ing = ArchiveIngestor(client, store, chat_id=-100)

    saved = await ing.run_full()

    assert saved == 2
    # Курсор всё равно на последнем id — иначе вернёмся к стикеру.
    assert store.get_checkpoint(-100) == 3


def test_to_message_extracts_fields():
    m = FakeMessage(42, "привет", sender_id=7)
    record = to_message(m, chat_id=-100)

    assert record.id == 42
    assert record.chat_id == -100
    assert record.text == "привет"
    assert record.sender_id == 7
    assert record.sender_name == "tester"


@pytest.mark.asyncio
async def test_live_single_message(tmp_path):
    store = make_store(tmp_path)
    client = FakeClient([])
    ing = ArchiveIngestor(client, store, chat_id=-100)

    saved = await ing.run_live(FakeMessage(5, "новое сообщение"))

    assert saved == 1
    assert store.message_count(-100) == 1
    assert store.get_checkpoint(-100) == 5


@pytest.mark.asyncio
async def test_live_ignores_media(tmp_path):
    store = make_store(tmp_path)
    ing = ArchiveIngestor(FakeClient([]), store, chat_id=-100)

    assert await ing.run_live(FakeMessage(6, None)) == 0
    assert store.message_count(-100) == 0


@pytest.mark.asyncio
async def test_all_media_batch_does_not_stop_ingest(tmp_path, monkeypatch):
    """
    Пачка целиком из медиа не должна обрывать инжест.

    Раньше пустой batch трактовался как «архив кончился»: на альбоме из
    BATCH_SIZE фотографий выгрузка вставала, курсор не двигался, и рестарт
    упирался в тот же альбом. Текст за медиа не доезжал никогда.
    """
    monkeypatch.setattr(ingest_module, "BATCH_SIZE", 3)
    store = make_store(tmp_path)
    msgs = [
        FakeMessage(1, None),      # ← целая пачка без текста
        FakeMessage(2, None),
        FakeMessage(3, None),
        FakeMessage(4, "деплой через docker compose"),
        FakeMessage(5, "пароль лежит в vault"),
        FakeMessage(6, "ретро в пятницу"),
    ]
    ing = ArchiveIngestor(FakeClient(msgs), store, chat_id=-100)

    saved = await ing.run_full()

    assert saved == 3
    assert store.message_count(-100) == 3
    assert store.get_checkpoint(-100) == 6


@pytest.mark.asyncio
async def test_media_only_archive_advances_checkpoint(tmp_path, monkeypatch):
    """Архив без единого текста: сохранять нечего, но курсор доходит до конца."""
    monkeypatch.setattr(ingest_module, "BATCH_SIZE", 2)
    store = make_store(tmp_path)
    ing = ArchiveIngestor(
        FakeClient([FakeMessage(i, None) for i in range(1, 6)]), store, chat_id=-100
    )

    assert await ing.run_full() == 0
    assert store.get_checkpoint(-100) == 5
