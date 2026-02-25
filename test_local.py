#!/usr/bin/env python3
"""
Локальный тест IA-Mother бота
"""

import asyncio
import logging
import os
from pathlib import Path

from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25039464"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "9ebe53a317b075a5eb7f8ea577f7f733")
IA_MOTHER_BOT_TOKEN = os.getenv("IA_MOTHER_BOT_TOKEN", "7312496733:AAGkY8KzYeQt3ysjv0fW81fU_Zsjem8hLs4")

# Проверка переменных
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN]):
    print("❌ Нужны переменные: TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN")
    exit(1)

# Session file next to script so it works from any cwd
_session_path = str(Path(__file__).resolve().parent / "ia_mother_test")
client = TelegramClient(
    _session_path,
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    receive_updates=True,
)

@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and (e.text.strip().startswith("/start") or e.text.strip() == "/start")))
async def on_start(event):
    print(f"[DEBUG] on_start triggered, sender_id={event.sender_id}, text={event.text!r}")
    try:
        await event.respond(
            "🤖 IA-Mother — Master Bot\n\n"
            "Привет! Я главный бот Zero Bot платформы.\n\n"
            "Что я умею:\n"
            "🥚 Клонировать новых ботов\n"
            "🏪 Показывать маркетплейс скиллов\n"
            "💱 Обменивать Stars на IA-Coins\n"
            "📊 Статистика платформы\n\n"
            "Команды:\n"
            "/clone — Создать нового бота\n"
            "/marketplace — Маркетплейс\n"
            "/stats — Статистика\n\n"
            "Платформа Zero Bot v2.0 готова! 🚀"
        )
        logger.info(f"Start command from user {event.sender_id}")
    except Exception as e:
        logger.exception(f"Error in on_start: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/clone")))
async def on_clone(event):
    try:
        await event.respond(
            "🥚 Создание нового бота\n\n"
            "Сейчас создам для вас персонального Zero Bot!\n\n"
            "⏳ Процесс:\n"
            "1. Создаю NFT паспорт на Solana\n"
            "2. Регистрирую бота в BotFather\n"
            "3. Запускаю Docker контейнер\n"
            "4. Устанавливаю личность Ия\n\n"
            "🎉 Готово! Ваш бот будет готов через 30 секунд.\n\n"
            "(В реальной версии здесь будет полная интеграция)"
        )
        logger.info(f"Clone command from user {event.sender_id}")
    except Exception as e:
        logger.exception(f"Error in on_clone: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/marketplace")))
async def on_marketplace(event):
    try:
        await event.respond(
            "🏪 Маркетплейс Zero Bot\n\n"
            "Популярные скиллы:\n"
            "🌤 Weather — Прогноз погоды (FREE)\n"
            "🖼 Image Gen — Генерация картинок (25 IA-Coins)\n"
            "😂 Meme Master — Создание мемов (15 IA-Coins)\n"
            "📝 Code Review — Ревью кода (50 IA-Coins)\n\n"
            "Личности:\n"
            "🤖 Ия — Дружелюбный ассистент (FREE)\n"
            "😏 Саркастичный друг (15 IA-Coins)\n"
            "👨‍💼 Бизнес-консультант (30 IA-Coins)\n\n"
            "💰 Баланс: 100 IA-Coins\n\n"
            "(Полный маркетплейс в разработке)"
        )
        logger.info(f"Marketplace command from user {event.sender_id}")
    except Exception as e:
        logger.exception(f"Error in on_marketplace: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/stats")))
async def on_stats(event):
    try:
        await event.respond(
            "📊 Статистика Zero Bot Platform\n\n"
            "🤖 Активных ботов: 1,247\n"
            "👥 Пользователей: 3,891\n"
            "🛠 Скиллов в маркетплейсе: 156\n"
            "🎭 Личностей: 23\n"
            "💰 Оборот IA-Coins: 45,678\n\n"
            "Топ разработчики:\n"
            "1. @alice — 23 скилла\n"
            "2. @bob — 18 скиллов\n"
            "3. @carol — 12 скиллов\n\n"
            "🚀 Платформа растёт!"
        )
        logger.info(f"Stats command from user {event.sender_id}")
    except Exception as e:
        logger.exception(f"Error in on_stats: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and not e.text.strip().startswith("/")))
async def on_message(event):
    print(f"[DEBUG] on_message triggered, sender_id={event.sender_id}, text={event.text!r}")
    try:
        text = (event.text or "").strip().lower()
        if not text:
            return

        if "привет" in text or "hello" in text:
            await event.respond(
                "👋 Привет! Я IA-Mother — главный бот Zero Bot платформы.\n\n"
                "Используй /start чтобы увидеть все возможности!"
            )
        elif "помощь" in text or "help" in text:
            await event.respond(
                "🆘 Помощь\n\n"
                "/start — Главное меню\n"
                "/clone — Создать бота\n"
                "/marketplace — Маркетплейс\n"
                "/stats — Статистика\n\n"
                "Или просто пиши — я отвечу!"
            )
        else:
            await event.respond(
                f"Интересно! Ты написал: '{event.text}'\n\n"
                "Я пока в режиме демо, но скоро научусь отвечать на всё! 😊\n\n"
                "Попробуй команды: /start, /clone, /marketplace"
            )

        logger.info(f"Message from {event.sender_id}: {event.text}")
    except Exception as e:
        logger.exception(f"Error in on_message: {e}")


@client.on(events.NewMessage(incoming=True))
async def _log_all_incoming(event):
    """Log every incoming message to verify we receive updates."""
    print(f"[INCOMING] chat_id={event.chat_id} sender_id={event.sender_id} text={event.text!r}")


async def main():
    logger.info("🚀 Запускаю IA-Mother бота...")
    await client.start(bot_token=IA_MOTHER_BOT_TOKEN)
    me = await client.get_me()
    logger.info(f"✅ Бот запущен: @{me.username} ({me.first_name})")
    print("🤖 IA-Mother бот работает!")
    print("📱 Найди его в Telegram: @IAMotherBot")
    print("🛑 Ctrl+C для остановки")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())