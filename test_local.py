#!/usr/bin/env python3
"""
Локальный тест IA-Mother бота
"""

import asyncio
import os
from pathlib import Path

from telethon import TelegramClient, events
from loguru import logger

# Конфигурация
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25039464"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "9ebe53a317b075a5eb7f8ea577f7f733")
IA_MOTHER_BOT_TOKEN = os.getenv("IA_MOTHER_BOT_TOKEN", "7312496733:AAGkY8KzYeQt3ysjv0fW81fU_Zsjem8hLs4")

# Проверка переменных
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN]):
    print("❌ Нужны переменные: TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN")
    exit(1)

# Клиент
client = TelegramClient("ia_mother_test", TELEGRAM_API_ID, TELEGRAM_API_HASH)


@client.on(events.NewMessage(pattern="/start"))
async def on_start(event):
    await event.respond(
        "🤖 **IA-Mother — Master Bot**\n\n"
        "Привет! Я главный бот Zero Bot платформы.\n\n"
        "**Что я умею:**\n"
        "🥚 Клонировать новых ботов\n"
        "🏪 Показывать маркетплейс скиллов\n"
        "💱 Обменивать Stars на IA-Coins\n"
        "📊 Статистика платформы\n\n"
        "**Команды:**\n"
        "/clone — Создать нового бота\n"
        "/marketplace — Маркетплейс\n"
        "/stats — Статистика\n\n"
        "Платформа Zero Bot v2.0 готова! 🚀"
    )
    logger.info(f"Start command from user {event.sender_id}")


@client.on(events.NewMessage(pattern="/clone"))
async def on_clone(event):
    await event.respond(
        "🥚 **Создание нового бота**\n\n"
        "Сейчас создам для вас персонального Zero Bot!\n\n"
        "⏳ Процесс:\n"
        "1. Создаю NFT паспорт на Solana\n"
        "2. Регистрирую бота в BotFather\n"
        "3. Запускаю Docker контейнер\n"
        "4. Устанавливаю личность 'Ия'\n\n"
        "🎉 Готово! Ваш бот будет готов через 30 секунд.\n\n"
        "*(В реальной версии здесь будет полная интеграция)*"
    )
    logger.info(f"Clone command from user {event.sender_id}")


@client.on(events.NewMessage(pattern="/marketplace"))
async def on_marketplace(event):
    await event.respond(
        "🏪 **Маркетплейс Zero Bot**\n\n"
        "**Популярные скиллы:**\n"
        "🌤 Weather — Прогноз погоды (FREE)\n"
        "🖼 Image Gen — Генерация картинок (25 IA-Coins)\n"
        "😂 Meme Master — Создание мемов (15 IA-Coins)\n"
        "📝 Code Review — Ревью кода (50 IA-Coins)\n\n"
        "**Личности:**\n"
        "🤖 Ия — Дружелюбный ассистент (FREE)\n"
        "😏 Саркастичный друг (15 IA-Coins)\n"
        "👨‍💼 Бизнес-консультант (30 IA-Coins)\n\n"
        "💰 Баланс: 100 IA-Coins\n\n"
        "*(Полный маркетплейс в разработке)*"
    )
    logger.info(f"Marketplace command from user {event.sender_id}")


@client.on(events.NewMessage(pattern="/stats"))
async def on_stats(event):
    await event.respond(
        "📊 **Статистика Zero Bot Platform**\n\n"
        "🤖 Активных ботов: 1,247\n"
        "👥 Пользователей: 3,891\n"
        "🛠 Скиллов в маркетплейсе: 156\n"
        "🎭 Личностей: 23\n"
        "💰 Оборот IA-Coins: 45,678\n\n"
        "**Топ разработчики:**\n"
        "1. @alice — 23 скилла\n"
        "2. @bob — 18 скиллов\n"
        "3. @carol — 12 скиллов\n\n"
        "🚀 Платформа растёт!"
    )
    logger.info(f"Stats command from user {event.sender_id}")


@client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith("/")))
async def on_message(event):
    text = event.text.lower()
    
    if "привет" in text or "hello" in text:
        await event.respond(
            "👋 Привет! Я IA-Mother — главный бот Zero Bot платформы.\n\n"
            "Используй /start чтобы увидеть все возможности!"
        )
    elif "помощь" in text or "help" in text:
        await event.respond(
            "🆘 **Помощь**\n\n"
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