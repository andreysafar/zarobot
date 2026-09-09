"""
Полная выгрузка архива чата через пользовательскую сессию Telethon.

Ключевые правила (из CLAUDE.md):
  — входим пользователем-администратором, НЕ бот-токеном;
  — пагинация курсором (min_id), а не get_messages(limit=N) как «весь архив»;
  — чекпоинт сохраняется после каждой пачки;
  — FloodWaitError — спим и продолжаем с последнего чекпоинта;
  — iter_messages только читает, историю прочитанной не помечает.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger
from telethon.errors import FloodWaitError, RPCError

from .store import Message, Store

# Сколько сообщений забираем за один проход перед сохранением чекпоинта.
BATCH_SIZE = int(__import__("os").getenv("DERVALER_BATCH_SIZE", "500"))
# Пауза между пачками: Telethon сам ждёт 1с при limit>3000, но для полного
# архива задаём wait_time явно, иначе ловим FloodWait на больших чатах.
WAIT_TIME = float(__import__("os").getenv("DERVALER_WAIT_TIME", "1.0"))


def _sender_name(sender) -> str | None:
    """Человекочитаемое имя отправителя."""
    if sender is None:
        return None
    if getattr(sender, "username", None):
        return sender.username
    parts = [getattr(sender, "first_name", None), getattr(sender, "last_name", None)]
    name = " ".join(p for p in parts if p)
    return name or None


def to_message(telegram_message, chat_id: int) -> Message:
    """Преобразовать сообщение Telethon в запись архива."""
    date = getattr(telegram_message, "date", None)
    if date is None:
        date = datetime.now(timezone.utc)
    elif date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)

    return Message(
        id=telegram_message.id,
        chat_id=chat_id,
        date=date,
        sender_id=getattr(telegram_message, "sender_id", None),
        sender_name=_sender_name(getattr(telegram_message, "sender", None)),
        text=getattr(telegram_message, "text", None) or getattr(telegram_message, "message", None),
        reply_to=getattr(telegram_message, "reply_to_msg_id", None),
    )


class ArchiveIngestor:
    """Выгружает историю чата порциями, сохраняя курсор."""

    def __init__(self, client, store: Store, chat_id: int):
        self.client = client
        self.store = store
        self.chat_id = chat_id

    async def run_full(self, max_messages: int | None = None) -> int:
        """
        Полный проход по архиву: от старых сообщений к новым.

        Возвращает количество сохранённых сообщений.
        Курсор берётся из БД, поэтому рестарт продолжает с того же места.
        """
        checkpoint = self.store.get_checkpoint(self.chat_id)
        total = 0
        logger.info(
            "Начинаю инжест чата {} (курсор={})", self.chat_id, checkpoint
        )

        while True:
            # Не читаем больше, чем осталось до лимита — иначе курсор
            # обгонит сохранённое.
            remaining = None
            if max_messages is not None:
                remaining = max_messages - total
                if remaining <= 0:
                    break

            try:
                saved, last_id, got_any = await self._ingest_batch(checkpoint, limit=remaining)
            except FloodWaitError as e:
                # Нас просят подождать. Ждём и повторяем с тем же курсором.
                logger.warning("FloodWait {} с. Жду и продолжаю.", e.seconds)
                await asyncio.sleep(e.seconds + 1)
                continue
            except RPCError as e:
                logger.error("RPC-ошибка при инжесте: {}", e)
                # Курсор уже сохранён внутри _ingest_batch — выходим, чтобы
                # следующий запуск продолжил, а не падал в бесконечный цикл.
                break

            total += saved
            if not got_any or last_id is None:
                break  # Архив исчерпан.

            checkpoint = last_id
            if max_messages is not None and total >= max_messages:
                logger.info("Достигнут лимит {} сообщений — останавливаюсь.", max_messages)
                break

        logger.info(
            "Инжест чата {} завершён. Сохранено {}. Курсор={}",
            self.chat_id, total, self.store.get_checkpoint(self.chat_id),
        )
        return total

    async def _ingest_batch(
        self, min_id: int, limit: int | None = None
    ) -> tuple[int, int | None, bool]:
        """
        Одна пачка: читаем не более `limit` сообщений начиная после min_id.

        Возвращает (сохранено, последний_id, были_ли_сообщения).
        Чекпоинт пишется СРАЗУ после пачки — это гарантия возобновления.

        ВАЖНО: `limit` ограничивает и чтение, и накопление. Иначе курсор
        уезжает вперёд сильнее, чем реально сохранено, и часть архива
        при рестарте теряется.
        """
        batch_limit = limit if limit is not None else BATCH_SIZE
        kwargs: dict = {"reverse": True, "wait_time": WAIT_TIME, "limit": batch_limit}
        if min_id:
            kwargs["min_id"] = min_id

        batch: list[Message] = []
        last_id: int | None = None
        read = 0

        async for message in self.client.iter_messages(self.chat_id, **kwargs):
            last_id = message.id
            read += 1
            # Сообщения без текста (медиа, стикеры) в архив не идут.
            if getattr(message, "text", None):
                batch.append(to_message(message, self.chat_id))
            if len(batch) >= batch_limit:
                break

        # Признак конца архива — что НИЧЕГО не прочитали. Пустой batch при
        # непустом чтении означает лишь пачку из одних медиа: если считать
        # её концом, инжест встанет на первом же альбоме фотографий и после
        # рестарта упрётся в него снова (курсор-то не сдвинулся).
        if last_id is None:
            return 0, None, False

        saved = self.store.add_messages(self.chat_id, batch) if batch else 0
        # Курсор двигаем по максимальному прочитанному id, даже если весь
        # батч оказался без текста.
        self.store.set_checkpoint(self.chat_id, last_id)

        logger.debug(
            "Пачка чата {}: прочитано {}, сохранено {}, курсор={}",
            self.chat_id, read, saved, last_id,
        )
        return saved, last_id, True

    async def run_live(self, message) -> int:
        """
        Добавить одно новое сообщение (из обработчика NewMessage).

        Возвращает количество сохранённых (0 или 1).
        """
        record = to_message(message, self.chat_id)
        if not record.text:
            return 0
        saved = self.store.add_messages(self.chat_id, [record])
        self.store.set_checkpoint(self.chat_id, record.id)
        return saved
