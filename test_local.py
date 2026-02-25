#!/usr/bin/env python3
"""Локальный тест IA-Mother бота."""

import asyncio
import logging
import os
from pathlib import Path

from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25039464"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "9ebe53a317b075a5eb7f8ea577f7f733")
IA_MOTHER_BOT_TOKEN = os.getenv("IA_MOTHER_BOT_TOKEN", "7312496733:AAGkY8KzYeQt3ysjv0fW81fU_Zsjem8hLs4")

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN]):
    print("❌ Нужны переменные: TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN")
    exit(1)

_session_path = str(Path(__file__).resolve().parent / "ia_mother_test")
client = TelegramClient(_session_path, TELEGRAM_API_ID, TELEGRAM_API_HASH, receive_updates=True)

# Command and message responses (single source of truth)
CMD_START = (
    "🤖 IA-Mother — Master Bot\n\n"
    "Привет! Я главный бот Zero Bot платформы.\n\n"
    "Что я умею:\n"
    "🥚 Клонировать новых ботов\n🏪 Показывать маркетплейс скиллов\n"
    "💱 Обменивать Stars на IA-Coins\n📊 Статистика платформы\n\n"
    "Команды:\n/clone — Создать нового бота\n/marketplace — Маркетплейс\n/stats — Статистика\n\n"
    "Платформа Zero Bot v2.0 готова! 🚀"
)
CMD_CLONE = (
    "🥚 Создание нового бота\n\n"
    "Сейчас создам для вас персонального Zero Bot!\n\n"
    "⏳ Процесс:\n1. Создаю NFT паспорт на Solana\n2. Регистрирую бота в BotFather\n"
    "3. Запускаю Docker контейнер\n4. Устанавливаю личность Ия\n\n"
    "🎉 Готово! Ваш бот будет готов через 30 секунд.\n\n"
    "(В реальной версии здесь будет полная интеграция)"
)
CMD_MARKETPLACE = (
    "🏪 Маркетплейс Zero Bot\n\n"
    "Популярные скиллы:\n🌤 Weather — Прогноз погоды (FREE)\n"
    "🖼 Image Gen — Генерация картинок (25 IA-Coins)\n😂 Meme Master — Создание мемов (15 IA-Coins)\n"
    "📝 Code Review — Ревью кода (50 IA-Coins)\n\n"
    "Личности:\n🤖 Ия — Дружелюбный ассистент (FREE)\n😏 Саркастичный друг (15 IA-Coins)\n"
    "👨‍💼 Бизнес-консультант (30 IA-Coins)\n\n💰 Баланс: 100 IA-Coins\n\n(Полный маркетплейс в разработке)"
)
CMD_STATS = (
    "📊 Статистика Zero Bot Platform\n\n"
    "🤖 Активных ботов: 1,247\n👥 Пользователей: 3,891\n🛠 Скиллов в маркетплейсе: 156\n"
    "🎭 Личностей: 23\n💰 Оборот IA-Coins: 45,678\n\n"
    "Топ разработчики:\n1. @alice — 23 скилла\n2. @bob — 18 скиллов\n3. @carol — 12 скиллов\n\n🚀 Платформа растёт!"
)
MSG_GREETING = (
    "👋 Привет! Я IA-Mother — главный бот Zero Bot платформы.\n\n"
    "Используй /start чтобы увидеть все возможности!"
)
MSG_HELP = (
    "🆘 Помощь\n\n"
    "/start — Главное меню\n/clone — Создать бота\n/marketplace — Маркетплейс\n/stats — Статистика\n\n"
    "Или просто пиши — я отвечу!"
)
MSG_DEFAULT = (
    "Интересно! Ты написал: '{text}'\n\n"
    "Я пока в режиме демо, но скоро научусь отвечать на всё! 😊\n\n"
    "Попробуй команды: /start, /clone, /marketplace"
)


def _is_cmd(text: str, prefix: str) -> bool:
    t = (text or "").strip()
    return t.startswith(prefix) if t else False


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and _is_cmd(e.text, "/start")))
async def on_start(event):
    try:
        await event.respond(CMD_START)
        logger.info("Start from user %s", event.sender_id)
    except Exception as e:
        logger.exception("Error in on_start: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and _is_cmd(e.text, "/clone")))
async def on_clone(event):
    try:
        await event.respond(CMD_CLONE)
        logger.info("Clone from user %s", event.sender_id)
    except Exception as e:
        logger.exception("Error in on_clone: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and _is_cmd(e.text, "/marketplace")))
async def on_marketplace(event):
    try:
        await event.respond(CMD_MARKETPLACE)
        logger.info("Marketplace from user %s", event.sender_id)
    except Exception as e:
        logger.exception("Error in on_marketplace: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and _is_cmd(e.text, "/stats")))
async def on_stats(event):
    try:
        await event.respond(CMD_STATS)
        logger.info("Stats from user %s", event.sender_id)
    except Exception as e:
        logger.exception("Error in on_stats: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and not _is_cmd(e.text or "", "/")))
async def on_message(event):
    try:
        text = (event.text or "").strip().lower()
        if not text:
            return
        if "привет" in text or "hello" in text:
            await event.respond(MSG_GREETING)
        elif "помощь" in text or "help" in text:
            await event.respond(MSG_HELP)
        else:
            await event.respond(MSG_DEFAULT.format(text=event.text))
        logger.info("Message from %s: %s", event.sender_id, event.text)
    except Exception as e:
        logger.exception("Error in on_message: %s", e)


async def main():
    logger.info("🚀 Запускаю IA-Mother бота...")
    await client.start(bot_token=IA_MOTHER_BOT_TOKEN)
    me = await client.get_me()
    logger.info("✅ Бот запущен: @%s (%s)", me.username, me.first_name)
    print("🤖 IA-Mother бот работает! 📱 @IAMotherBot  🛑 Ctrl+C")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
