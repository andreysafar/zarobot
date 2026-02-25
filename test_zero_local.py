#!/usr/bin/env python3
"""
Локальный тест Zero Bot instance с личностью Ия.
С API-ключом (OPENROUTER_API_KEY, OPENAI_API_KEY или ANTHROPIC_API_KEY) ответы через LLM;
без ключа — по ключевым словам.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from telethon import TelegramClient, events

import test_zero_local_llm as llm_mod
from test_zero_local_responses import get_fallback_response, get_keyword_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Config
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "25039464"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "9ebe53a317b075a5eb7f8ea577f7f733")
ZERO_BOT_TOKEN = os.getenv("ZERO_BOT_TOKEN", "477216183:AAH35Z0PD9UDiZx1_gIOWpdQrxxq_L6v6Gk")
LLM_ENABLED = bool(
    os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
)

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, ZERO_BOT_TOKEN]):
    print("❌ Нужны переменные: TELEGRAM_API_ID, TELEGRAM_API_HASH, ZERO_BOT_TOKEN")
    exit(1)

# Personality
personality_dir = Path(__file__).resolve().parent / "personalities" / "ia"
manifest_path = personality_dir / "manifest.json"
if not manifest_path.exists():
    print(f"❌ Не найден манифест личности: {manifest_path}")
    exit(1)

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
prompts_dir = personality_dir / "prompts"
system_prompt_free = (prompts_dir / "system_free.txt").read_text(encoding="utf-8").strip()
system_prompt_full = (prompts_dir / "system.txt").read_text(encoding="utf-8").strip()
system_prompt = system_prompt_full or system_prompt_free
greeting_template = (prompts_dir / "greeting.txt").read_text(encoding="utf-8").strip()
fallback = (prompts_dir / "fallback.txt").read_text(encoding="utf-8").strip()

logger.info("Загружена личность: %s", manifest["display_name"])
logger.info("LLM: %s", "включён" if LLM_ENABLED else "выключен (ключевые слова)")

# Telegram client
_session_path = str(Path(__file__).resolve().parent / "zero_bot_test")
client = TelegramClient(_session_path, TELEGRAM_API_ID, TELEGRAM_API_HASH, receive_updates=True)

bot_state = {"level": 0, "xp": 0, "messages_total": 0, "personality": manifest["display_name"]}
MAX_HISTORY = 10
chat_history: dict[int, list[dict[str, str]]] = {}


def get_greeting(user_name: str) -> str:
    try:
        return greeting_template.format(user_name=user_name, bot_name=manifest["display_name"])
    except KeyError:
        return greeting_template


async def process_message(text: str, user_name: str, user_id: int) -> str:
    if LLM_ENABLED:
        if user_id not in chat_history:
            chat_history[user_id] = []
        history = chat_history[user_id][-MAX_HISTORY:]
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": text})
        reply = await llm_mod.call_llm(system_prompt, messages, fallback)
        chat_history[user_id].append({"role": "user", "content": text})
        chat_history[user_id].append({"role": "assistant", "content": reply})
        return reply
    kw = get_keyword_response(text, user_name)
    return kw if kw is not None else get_fallback_response(text)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/start")))
async def on_start(event):
    try:
        sender = await event.get_sender()
        name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
        await event.respond(get_greeting(name))
        logger.info("Start from %s (%s)", name, event.sender_id)
    except Exception as e:
        logger.exception("Error in on_start: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/stats")))
async def on_stats(event):
    try:
        await event.respond(
            f"📊 {manifest['display_name']}\n\n"
            f"Level: {bot_state['level']}\nXP: {bot_state['xp']}\n"
            f"Messages: {bot_state['messages_total']}\nPersonality: {bot_state['personality']}\n\n"
            f"🧠 AI Model: {manifest['ai_model']['preferred']}\n"
            f"🎭 Style: {manifest['behavior']['response_style']}\n🌍 Language: {manifest['language']}"
        )
    except Exception as e:
        logger.exception("Error in on_stats: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and e.text.strip().startswith("/help")))
async def on_help(event):
    try:
        await event.respond(
            f"🤖 {manifest['display_name']}\n\n"
            "Команды:\n/start — Приветствие\n/stats — Статистика\n/help — Помощь\n\n"
            "Просто пишите — я отвечу!\n(В полной версии: скиллы, картинки, мемы, поиск)"
        )
    except Exception as e:
        logger.exception("Error in on_help: %s", e)


@client.on(events.NewMessage(incoming=True, func=lambda e: e.text and not (e.text or "").strip().startswith("/")))
async def on_message(event):
    try:
        text = (event.text or "").strip()
        if not text:
            return
        sender = await event.get_sender()
        name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
        response = await process_message(text, name, event.sender_id)
        await event.respond(response)
        bot_state["xp"] += 1
        bot_state["messages_total"] += 1
        if bot_state["xp"] >= (bot_state["level"] + 1) * 100:
            bot_state["level"] += 1
            await event.respond(f"🎉 Level UP! Теперь я {bot_state['level']} уровня!")
        logger.info("Message from %s: %s...", name, text[:50])
    except Exception as e:
        logger.exception("Error in on_message: %s", e)


async def main():
    logger.info("🚀 Запускаю Zero Bot с личностью Ия...")
    await client.start(bot_token=ZERO_BOT_TOKEN)
    me = await client.get_me()
    logger.info("✅ Бот запущен: @%s (%s)", me.username, me.first_name)
    print("🤖 Zero Bot (%s) работает! 📱 @Safar_test_bot  🛑 Ctrl+C" % manifest["display_name"])
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
