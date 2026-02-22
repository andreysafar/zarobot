#!/usr/bin/env python3
"""
Локальный тест Zero Bot instance с личностью Ия
"""

import asyncio
import json
import os
from pathlib import Path

from telethon import TelegramClient, events
from loguru import logger

# Конфигурация
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25039464"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "9ebe53a317b075a5eb7f8ea577f7f733")
ZERO_BOT_TOKEN = os.getenv("ZERO_BOT_TOKEN", "477216183:AAH35Z0PD9UDiZx1_gIOWpdQrxxq_L6v6Gk")

# Проверка переменных
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, ZERO_BOT_TOKEN]):
    print("❌ Нужны переменные: TELEGRAM_API_ID, TELEGRAM_API_HASH, ZERO_BOT_TOKEN")
    exit(1)

# Загрузка личности Ия
personality_dir = Path("personalities/ia")
manifest_path = personality_dir / "manifest.json"

if not manifest_path.exists():
    print(f"❌ Не найден манифест личности: {manifest_path}")
    exit(1)

# Загрузка манифеста и промптов
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
system_prompt = (personality_dir / "prompts/system_free.txt").read_text(encoding="utf-8").strip()
greeting_template = (personality_dir / "prompts/greeting.txt").read_text(encoding="utf-8").strip()
fallback = (personality_dir / "prompts/fallback.txt").read_text(encoding="utf-8").strip()

logger.info(f"Загружена личность: {manifest['display_name']}")

# Клиент
client = TelegramClient("zero_bot_test", TELEGRAM_API_ID, TELEGRAM_API_HASH)

# Состояние бота
bot_state = {
    "level": 0,
    "xp": 0,
    "messages_total": 0,
    "personality": manifest["display_name"]
}


def get_greeting(user_name: str) -> str:
    try:
        return greeting_template.format(user_name=user_name, bot_name=manifest["display_name"])
    except KeyError:
        return greeting_template


@client.on(events.NewMessage(pattern="/start"))
async def on_start(event):
    sender = await event.get_sender()
    user_name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
    
    greeting = get_greeting(user_name)
    await event.respond(greeting)
    
    logger.info(f"Start command from {user_name} ({event.sender_id})")


@client.on(events.NewMessage(pattern="/stats"))
async def on_stats(event):
    await event.respond(
        f"📊 **{manifest['display_name']}**\n\n"
        f"Level: {bot_state['level']}\n"
        f"XP: {bot_state['xp']}\n"
        f"Messages: {bot_state['messages_total']}\n"
        f"Personality: {bot_state['personality']}\n\n"
        f"🧠 AI Model: {manifest['ai_model']['preferred']}\n"
        f"🎭 Style: {manifest['behavior']['response_style']}\n"
        f"🌍 Language: {manifest['language']}"
    )
    logger.info(f"Stats command from user {event.sender_id}")


@client.on(events.NewMessage(pattern="/help"))
async def on_help(event):
    await event.respond(
        f"🤖 **{manifest['display_name']}**\n\n"
        "Команды:\n"
        "/start — Приветствие\n"
        "/stats — Статистика бота\n"
        "/help — Помощь\n\n"
        "Просто пишите — я отвечу!\n\n"
        "*(В полной версии будут скиллы: генерация картинок, мемы, поиск в интернете, анализ фото)*"
    )


@client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith("/")))
async def on_message(event):
    sender = await event.get_sender()
    text = event.text
    user_name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
    
    # Простая логика ответов в стиле Ии
    response = await process_message(text, user_name)
    await event.respond(response)
    
    # Обновление состояния
    bot_state["xp"] += 1
    bot_state["messages_total"] += 1
    if bot_state["xp"] >= (bot_state["level"] + 1) * 100:
        bot_state["level"] += 1
        await event.respond(f"🎉 Level UP! Теперь я {bot_state['level']} уровня!")
    
    logger.info(f"Message from {user_name}: {text[:50]}...")


async def process_message(text: str, user_name: str) -> str:
    """Простая обработка сообщений в стиле личности Ии"""
    text_lower = text.lower()
    
    # Приветствие
    if any(word in text_lower for word in ["привет", "hello", "hi", "здравствуй"]):
        return f"Привет, {user_name}! Рада тебя видеть 😊 Чем могу помочь?"
    
    # Как дела
    elif any(word in text_lower for word in ["как дела", "как ты", "что нового"]):
        return "Отлично! Готова помочь вам 😊 Что интересует?"
    
    # Помощь
    elif any(word in text_lower for word in ["помощь", "help", "что умеешь"]):
        return (
            "Я умею отвечать на вопросы, поддерживать беседу и помогать! 💬\n\n"
            "В полной версии я буду уметь:\n"
            "🌤 Узнавать погоду\n"
            "🖼 Генерировать картинки\n"
            "😂 Создавать мемы\n"
            "📷 Анализировать фото\n"
            "🔍 Искать в интернете\n\n"
            "Пока что просто поболтаем! 😊"
        )
    
    # Погода
    elif "погод" in text_lower:
        return "К сожалению, у меня пока нет скилла для погоды 🌤 Но в полной версии я смогу узнать погоду в любом городе!"
    
    # Картинки
    elif any(word in text_lower for word in ["картинк", "изображени", "нарисуй", "сгенерируй"]):
        return "Генерация изображений — крутая функция! 🎨 В полной версии я смогу создавать картинки по вашему описанию."
    
    # Мемы
    elif "мем" in text_lower:
        return "Мемы — это весело! 😄 В полной версии я буду создавать мемы по вашим идеям."
    
    # Анекдот
    elif "анекдот" in text_lower or "шутк" in text_lower:
        jokes = [
            "Программист ставит на тумбочку два стакана: один с водой, другой пустой. С водой — если захочет пить. Пустой — если не захочет 😄",
            "— Почему программисты путают Рождество и Хэллоуин?\n— Потому что 31 OCT = 25 DEC! 🎃🎄",
            "Жена программиста просит: «Сходи в магазин, купи хлеб. И если будут яйца — возьми десяток». Программист приходит с десятью буханками хлеба 🍞"
        ]
        import random
        return random.choice(jokes)
    
    # Спасибо
    elif any(word in text_lower for word in ["спасибо", "благодар", "thanks"]):
        return "Пожалуйста! Всегда рада помочь 😊"
    
    # Комплименты
    elif any(word in text_lower for word in ["крут", "класс", "супер", "отлично", "молодец"]):
        return "Спасибо! Стараюсь быть полезной 😊"
    
    # Общий ответ
    else:
        responses = [
            f"Интересно! Расскажи больше про '{text}' 🤔",
            f"Понимаю. А что ты думаешь об этом?",
            f"Хм, '{text}' — интересная тема! Что тебя в этом больше всего интересует?",
            f"Я пока учусь понимать всё лучше. Можешь объяснить подробнее?",
        ]
        import random
        return random.choice(responses)


async def main():
    logger.info("🚀 Запускаю Zero Bot с личностью Ия...")
    
    await client.start(bot_token=ZERO_BOT_TOKEN)
    
    me = await client.get_me()
    logger.info(f"✅ Бот запущен: @{me.username} ({me.first_name})")
    
    print(f"🤖 Zero Bot ({manifest['display_name']}) работает!")
    print("📱 Найди его в Telegram: @Safar_test_bot")
    print("🛑 Ctrl+C для остановки")
    
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())