#!/usr/bin/env python3
"""
Локальный тест Zero Bot instance с личностью Ия.
С API-ключом (OPENROUTER_API_KEY, OPENAI_API_KEY или ANTHROPIC_API_KEY) ответы идут через LLM;
без ключа — только ключевые слова (без токенов).
"""

import asyncio
import json
import logging
import os
import random
from pathlib import Path

from telethon import TelegramClient, events

# Optional LLM clients (pip install openai anthropic)
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25039464"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "9ebe53a317b075a5eb7f8ea577f7f733")
ZERO_BOT_TOKEN = os.getenv("ZERO_BOT_TOKEN", "477216183:AAH35Z0PD9UDiZx1_gIOWpdQrxxq_L6v6Gk")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_ENABLED = bool(OPENAI_API_KEY or ANTHROPIC_API_KEY or OPENROUTER_API_KEY)

# Проверка переменных
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, ZERO_BOT_TOKEN]):
    print("❌ Нужны переменные: TELEGRAM_API_ID, TELEGRAM_API_HASH, ZERO_BOT_TOKEN")
    exit(1)

# Загрузка личности Ия (путь относительно скрипта, чтобы работало из любой cwd)
personality_dir = Path(__file__).resolve().parent / "personalities" / "ia"
manifest_path = personality_dir / "manifest.json"

if not manifest_path.exists():
    print(f"❌ Не найден манифест личности: {manifest_path}")
    exit(1)

# Загрузка манифеста и промптов
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
system_prompt_free = (personality_dir / "prompts/system_free.txt").read_text(encoding="utf-8").strip()
system_prompt_full = (personality_dir / "prompts/system.txt").read_text(encoding="utf-8").strip()
greeting_template = (personality_dir / "prompts/greeting.txt").read_text(encoding="utf-8").strip()
fallback = (personality_dir / "prompts/fallback.txt").read_text(encoding="utf-8").strip()

# System prompt for LLM: prefer full, fallback to free
system_prompt = system_prompt_full or system_prompt_free

logger.info(f"Загружена личность: {manifest['display_name']}")
if LLM_ENABLED:
    backend = "OpenRouter" if OPENROUTER_API_KEY else ("OpenAI" if OPENAI_API_KEY else "Anthropic")
    logger.info(f"LLM включён: ответы через {backend}")
else:
    logger.info("LLM выключен: ответы по ключевым словам (без токенов)")

# Session file next to script so it works from any cwd
_session_path = str(Path(__file__).resolve().parent / "zero_bot_test")
client = TelegramClient(
    _session_path,
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    receive_updates=True,
)

# Состояние бота
bot_state = {
    "level": 0,
    "xp": 0,
    "messages_total": 0,
    "personality": manifest["display_name"]
}

# Per-user chat history for LLM (last N messages)
MAX_HISTORY = 10
chat_history: dict[int, list[dict[str, str]]] = {}


def get_greeting(user_name: str) -> str:
    try:
        return greeting_template.format(user_name=user_name, bot_name=manifest["display_name"])
    except KeyError:
        return greeting_template


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/start")))
async def on_start(event):
    print(f"[DEBUG] on_start triggered, sender_id={event.sender_id}")
    try:
        sender = await event.get_sender()
        user_name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
        greeting = get_greeting(user_name)
        await event.respond(greeting)
        logger.info(f"Start command from {user_name} ({event.sender_id})")
    except Exception as e:
        logger.exception(f"Error in on_start: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/stats")))
async def on_stats(event):
    try:
        await event.respond(
            f"📊 {manifest['display_name']}\n\n"
            f"Level: {bot_state['level']}\n"
            f"XP: {bot_state['xp']}\n"
            f"Messages: {bot_state['messages_total']}\n"
            f"Personality: {bot_state['personality']}\n\n"
            f"🧠 AI Model: {manifest['ai_model']['preferred']}\n"
            f"🎭 Style: {manifest['behavior']['response_style']}\n"
            f"🌍 Language: {manifest['language']}"
        )
        logger.info(f"Stats command from user {event.sender_id}")
    except Exception as e:
        logger.exception(f"Error in on_stats: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/help")))
async def on_help(event):
    try:
        await event.respond(
            f"🤖 {manifest['display_name']}\n\n"
            "Команды:\n"
            "/start — Приветствие\n"
            "/stats — Статистика бота\n"
            "/help — Помощь\n\n"
            "Просто пишите — я отвечу!\n\n"
            "(В полной версии будут скиллы: генерация картинок, мемы, поиск в интернете, анализ фото)"
        )
        logger.info(f"Help command from user {event.sender_id}")
    except Exception as e:
        logger.exception(f"Error in on_help: {e}")


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and not (e.text or "").strip().startswith("/")))
async def on_message(event):
    print(f"[DEBUG] on_message triggered, sender_id={event.sender_id}, text={event.text!r}")
    try:
        text = (event.text or "").strip()
        if not text:
            return
        sender = await event.get_sender()
        user_name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")

        response = await process_message(text, user_name, event.sender_id)
        await event.respond(response)

        bot_state["xp"] += 1
        bot_state["messages_total"] += 1
        if bot_state["xp"] >= (bot_state["level"] + 1) * 100:
            bot_state["level"] += 1
            await event.respond(f"🎉 Level UP! Теперь я {bot_state['level']} уровня!")

        logger.info(f"Message from {user_name}: {text[:50]}...")
    except Exception as e:
        logger.exception(f"Error in on_message: {e}")


async def call_llm(user_id: int, text: str) -> str:
    """Call OpenRouter, OpenAI or Anthropic with personality system prompt and chat history."""
    if user_id not in chat_history:
        chat_history[user_id] = []
    history = chat_history[user_id][-MAX_HISTORY:]
    messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": text})

    reply = fallback
    if OPENROUTER_API_KEY and AsyncOpenAI:
        client_ai = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        try:
            r = await client_ai.chat.completions.create(
                model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001"),
                messages=messages,
                max_tokens=1024,
            )
            reply = (r.choices[0].message.content or "").strip() or fallback
        except Exception as e:
            logger.exception(f"OpenRouter error: {e}")
    elif OPENAI_API_KEY and AsyncOpenAI:
        client_ai = AsyncOpenAI(api_key=OPENAI_API_KEY)
        try:
            r = await client_ai.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                max_tokens=1024,
            )
            reply = (r.choices[0].message.content or "").strip() or fallback
        except Exception as e:
            logger.exception(f"OpenAI error: {e}")
    elif ANTHROPIC_API_KEY and AsyncAnthropic:
        client_ai = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        system = messages[0]["content"]
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages[1:]]
        try:
            r = await client_ai.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                max_tokens=1024,
                system=system,
                messages=api_messages,
            )
            reply = (r.content[0].text if r.content else "").strip() or fallback
        except Exception as e:
            logger.exception(f"Anthropic error: {e}")
    else:
        return fallback

    chat_history[user_id].append({"role": "user", "content": text})
    chat_history[user_id].append({"role": "assistant", "content": reply})
    return reply


async def process_message(text: str, user_name: str, user_id: int = 0) -> str:
    """Обработка сообщений: при включённом LLM — через API, иначе по ключевым словам."""
    if LLM_ENABLED:
        return await call_llm(user_id, text)

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


@client.on(events.NewMessage(incoming=True))
async def _log_all_incoming(event):
    print(f"[INCOMING] chat_id={event.chat_id} sender_id={event.sender_id} text={event.text!r}")


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