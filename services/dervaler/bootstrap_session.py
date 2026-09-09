"""
ОДНОКРАТНАЯ процедура входа администратора. Запускается оператором ВРУЧНУЮ.

    python -m services.dervaler.bootstrap_session

Что происходит:
  1. Telethon просит номер телефона, код из Telegram (или пароль 2FA).
  2. Сессия сохраняется в /data/dervaler/session (или выводится строкой,
     если задан BOOTSTRAP_PRINT_STRING=1 — тогда её кладут в DERVALER_SESSION).

Рантайм (worker.py) только переиспользует уже сохранённую сессию и НИКОГДА
не запрашивает код. Файл сессии эквивалентен паролю — не коммитить, не логировать.
"""

from __future__ import annotations

import asyncio
import os

from loguru import logger
from telethon import TelegramClient
from telethon.sessions import StringSession

from . import config as cfg


async def main() -> None:
    if not cfg.TELEGRAM_API_ID or not cfg.TELEGRAM_API_HASH:
        logger.error("Задайте TELEGRAM_API_ID и TELEGRAM_API_HASH в окружении.")
        return

    print_session = os.getenv("BOOTSTRAP_PRINT_STRING", "0") in ("1", "true", "yes")

    if print_session:
        session: str | StringSession = StringSession()
    else:
        session = str(cfg.session_path())

    client = TelegramClient(session, cfg.TELEGRAM_API_ID, cfg.TELEGRAM_API_HASH)

    await client.start()
    me = await client.get_me()
    logger.info(
        "Вход выполнен: {} (id={})",
        getattr(me, "username", None) or getattr(me, "first_name", "?"),
        getattr(me, "id", "?"),
    )

    if print_session:
        # Печатаем строку сессии — положить в DERVALER_SESSION.
        logger.warning(
            "Сохраните эту строку в DERVALER_SESSION (секрет!):\n{}",
            client.session.save(),
        )
    else:
        logger.info("Сессия сохранена в {}", cfg.session_path())

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
