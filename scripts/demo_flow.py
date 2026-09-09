"""
Локальный сквозной прогон БЕЗ Telegram и без Docker.

Показывает весь флоу целиком:
  1. Дервалер «выгружает» историю чата (фейковый клиент) → SQLite.
  2. Админ добавляет запись в FAQ и публикует её.
  3. Хелпер отвечает на вопросы, используя ту же базу.

Запуск:
    python scripts/demo_flow.py

Это НЕ заменяет ручной тест в живом чате, но позволяет проверить
стык компонентов за секунды и без секретов.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdk"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "services" / "bot-instance"))

from dervaler.ingest import ArchiveIngestor  # noqa: E402
from zero_bot_sdk import SkillContext  # noqa: E402
from dervaler.store import Store  # noqa: E402

CHAT_ID = -1001234567890


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeMessage:
    """Аналог сообщения Telethon."""

    def __init__(self, id_, text, sender="Аня"):
        self.id = id_
        self.text = text
        self.message = text
        self.date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.sender_id = 1
        self.sender = SimpleNamespace(first_name=sender, last_name=None, username=sender)
        self.reply_to_msg_id = None


class FakeClient:
    """Фейк клиента Telethon: отдаёт архив по min_id."""

    def __init__(self, messages):
        self.messages = sorted(messages, key=lambda m: m.id)

    async def iter_messages(self, chat_id, **kwargs):
        min_id = kwargs.get("min_id", 0)
        limit = kwargs.get("limit", 500)
        for m in self.messages:
            if m.id > min_id:
                yield m
            if m.id > min_id and limit and m.id > min_id + limit:
                break


# Архив: факты, которые должен знать хелпер.
ARCHIVE = [
    (1, "Всем привет, я новенькая"),
    (2, "Деплой делается командой docker compose up -d --build"),
    (3, "Пароль от админки лежит в vault, спрашивать у Саши"),
    (4, "Стенд для тестов подняли на сервере 10.0.0.5"),
    (5, "Обычная болтовня ни о чём"),
    (6, "Ретроспектива назначена на пятницу"),
]


def hr(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


async def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="zero_demo_"))
    db_path = tmp / "archive.sqlite3"

    hr("ЭТАП 1. Дервалер выгружает архив чата")
    store = Store(db_path)
    client = FakeClient([FakeMessage(i, t) for i, t in ARCHIVE])
    ingestor = ArchiveIngestor(client, store, chat_id=CHAT_ID)

    saved = await ingestor.run_full()
    print(f"Сохранено сообщений: {saved}")
    print(f"Курсор инжеста:      {store.get_checkpoint(CHAT_ID)}")

    hr("ЭТАП 2. Админ ведёт FAQ")
    # Здесь имитируем права админа через OWNER_ID.
    os.environ["OWNER_ID"] = "555"
    skill_mod = load(
        "helper_kb_handler", ROOT / "examples" / "skill-helper-kb" / "handler.py"
    )
    skill = skill_mod.HelperKbSkill(store=store, telegram_client=None)

    def ctx(is_private: bool = False) -> SkillContext:
        """Настоящий контекст рантайма, а не заглушка."""
        return SkillContext(
            bot_id="demo", user_id=555, chat_id=CHAT_ID,
            config={"is_private": is_private},
        )

    # Проходим тем же путём, что и бот: on_install подключает LLM-судью,
    # если в окружении есть ключ провайдера.
    await skill.on_install(ctx())
    print(
        "Режим ответов: "
        + ("LLM-судья" if skill.llm_call else "цитаты (ключ LLM не задан)")
    )

    first_add = await skill.on_command(
        ctx(), "/faq_add", "Как деплоить? | docker compose up -d --build"
    )
    print(first_add.text)
    add_resp = await skill.on_command(
        ctx(), "/faq_add", "Где пароль от админки? | В vault, спросить у Саши"
    )
    faq_id = add_resp.text.split("#")[1].split()[0]
    print(add_resp.text)
    print((await skill.on_command(ctx(), "/faq_publish", "1")).text)
    print((await skill.on_command(ctx(), "/faq_publish", faq_id)).text)

    hr("ЭТАП 3. Хелпер отвечает на вопросы")
    questions = [
        "как деплоить?",
        "где пароль от админки?",
        "какой адрес у тестового стенда?",
        "когда ретроспектива?",
        "привет всем, как дела?",
    ]
    for q in questions:
        resp = await skill.on_message(ctx(), q)
        if resp.is_skip():
            print(f"\n❓ {q}\n   → [молчит — не вопрос или ничего не найдено]")
        else:
            first = resp.text.split("\n")[0][:70]
            print(f"\n❓ {q}\n   → {first}")

    hr("ЭТАП 4. FAQ и статус")
    print((await skill.on_command(ctx(), "/faq", "")).text)
    print()
    print((await skill.on_command(ctx(), "/ingest_status", "")).text)

    hr("ЭТАП 5. Живое обновление")
    before = store.get_checkpoint(CHAT_ID)
    await ingestor.run_live(FakeMessage(7, "Купили новый домен example.com"))
    print(f"Курсор: {before} → {store.get_checkpoint(CHAT_ID)}")
    resp = await skill.on_message(ctx(), "какой домен купили?")
    print(f"❓ какой домен купили?\n   → {resp.text.split(chr(10))[0][:70]}")

    store.close()

    hr("ГОТОВО")
    print(f"База: {db_path}")
    print("Всё работает без Telegram и Docker.\n")


if __name__ == "__main__":
    asyncio.run(main())
