"""
Дервалер — воркер-архивариус. Входит пользовательской сессией администратора,
выгружает полный архив чата и поддерживает базу знаний.

Это НЕ бот: он не отвечает в публичном чате и не использует бот-токен.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from loguru import logger
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from . import config as cfg
from .ingest import ArchiveIngestor, to_message
from .store import Store
from .summarizer import ChatSummarizer


def build_client() -> TelegramClient:
    """
    Создать клиент Telethon на пользовательской сессии.

    Приоритет: строка сессии из env (DERVALER_SESSION), иначе файл на диске.
    """
    if cfg.DERVALER_SESSION:
        session = StringSession(cfg.DERVALER_SESSION)
        logger.info("Использую сессию из DERVALER_SESSION")
    else:
        session = str(cfg.session_path())
        logger.info("Использую файл сессии: {}", session)

    return TelegramClient(
        session,
        cfg.TELEGRAM_API_ID,
        cfg.TELEGRAM_API_HASH,
        # Явно отключаем пометку прочитанным при чтении истории.
        sequential_updates=True,
    )


class Dervaler:
    """Воркер инжеста."""

    def __init__(self):
        self.client = build_client()
        self.store = Store(cfg.DB_PATH)
        self.chat_id = cfg.HELPER_CHAT_ID
        self.ingestor = ArchiveIngestor(self.client, self.store, self.chat_id)
        self.summarizer = ChatSummarizer(self.store, llm_call=self._llm, chat_id=self.chat_id)
        self.summarizer.set_prompt(self._load_summary_prompt())

    def _load_summary_prompt(self) -> str:
        """Промпт сводки из личности Дервалера."""
        path = Path(cfg.PERSONALITY_DIR) / "prompts" / "summary_agent.txt"
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning("Промпт сводки не найден ({}): {}", path, e)
            return "Обнови сводку чата по новым сообщениям."

    async def _llm(self, prompt: str) -> str | None:
        """Вызов LLM (OpenRouter). Без ключа сводка просто не обновляется."""
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            return None
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            r = await client.chat.completions.create(
                model=os.getenv("SUMMARY_MODEL", "deepseek/deepseek-v4-flash-0731"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=int(os.getenv("SUMMARY_MAX_TOKENS", "2000")),
            )
            return (r.choices[0].message.content or "").strip() or None
        except Exception as e:
            logger.warning("LLM для сводки недоступен: {}", e)
            return None

    async def notify_admin(self, text: str) -> None:
        """Статус — только в личку администратору, никогда в публичный чат."""
        if not cfg.ADMIN_ID:
            return
        try:
            await self.client.send_message(cfg.ADMIN_ID, text)
        except Exception as e:
            logger.warning("Не удалось отправить статус администратору: {}", e)

    async def run(self) -> None:
        if not cfg.chat_allowed(self.chat_id):
            logger.error("Чат {} не в белом списке — отказываюсь работать.", self.chat_id)
            return

        await self.client.start()
        me = await self.client.get_me()
        logger.info(
            "Дервалер вошёл как {} (id={}) — пользовательская сессия",
            getattr(me, "username", None) or getattr(me, "first_name", "?"),
            getattr(me, "id", "?"),
        )

        # 1. Полный проход по архиву.
        saved = await self.ingestor.run_full(max_messages=cfg.MAX_MESSAGES)
        total = self.store.message_count(self.chat_id)
        await self.notify_admin(
            f"Архив чата {self.chat_id}: сохранено {saved}, всего в базе {total}."
        )

        # 2. Живое дозаписывание новых сообщений.
        if cfg.LIVE_UPDATES:
            self._register_live()
            logger.info("Живое обновление включено для чата {}", self.chat_id)
            await self.client.run_until_disconnected()
        else:
            logger.info("Живое обновление отключено — завершаю работу.")

    def _register_live(self) -> None:
        """Обработчик новых сообщений: дозаписываем в архив, в чат не отвечаем."""
        dervaler = self

        @self.client.on(events.NewMessage(chats=[self.chat_id]))
        async def on_new(event):
            if not cfg.chat_allowed(event.chat_id):
                return
            try:
                saved = await dervaler.ingestor.run_live(event.message)
                if saved:
                    logger.debug("Дозаписано сообщение {}", event.message.id)
                    # Сырое сообщение уже в архиве; сводку обновим пачкой.
                    record = to_message(event.message, dervaler.chat_id)
                    await dervaler.summarizer.add({
                        "id": record.id,
                        "date": record.date.isoformat(),
                        "sender_name": record.sender_name,
                        "text": record.text,
                    })
            except Exception as e:
                logger.error("Ошибка live-обновления: {}", e)


async def main() -> None:
    problems = cfg.validate()
    if problems:
        for p in problems:
            logger.error("Конфигурация: {}", p)
        return

    dervaler = Dervaler()
    try:
        await dervaler.run()
    finally:
        # Досчитываем сводку по остатку, чтобы не терять накопленное.
        try:
            await dervaler.summarizer.flush(force=True)
        except Exception:
            pass
        dervaler.store.close()


if __name__ == "__main__":
    asyncio.run(main())
