#!/usr/bin/env python3
"""
Standalone Zero Bot — no Django, no Redis, no FastAPI.
Pure Telethon + Telegram Bot API.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

LOG_PATH = str(Path(__file__).parent / ".cursor" / "debug.log")

def _dbg(loc, msg, data=None, hypothesis_id=None):
    # #region agent log
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps({"id": f"log_{int(datetime.now().timestamp()*1000)}", "timestamp": int(datetime.now().timestamp()*1000), "location": loc, "message": msg, "data": data or {}, "runId": "zero_bot_run", "hypothesisId": hypothesis_id or ""}) + "\n")
    # #endregion

API_ID = 25039464
API_HASH = "9ebe53a317b075a5eb7f8ea577f7f733"
BOT_TOKEN = "477216183:AAH35Z0PD9UDiZx1_gIOWpdQrxxq_L6v6Gk"

from telethon import TelegramClient, events

async def main():
    _dbg("zero_bot:main", "Starting", {"api_id": API_ID, "token_prefix": BOT_TOKEN[:15]}, "H4")
    print(f"Starting Zero Bot...")
    print(f"  API ID: {API_ID}")
    print(f"  Token:  {BOT_TOKEN[:15]}...")

    client = TelegramClient("zero_bot_session", API_ID, API_HASH)

    # --- Handlers ---

    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        _dbg("zero_bot:start_handler", "/start received", {"sender": event.sender_id}, "H4")
        user = await event.get_sender()
        await event.respond(
            f"🤖 **Zero Bot**\n\n"
            f"Привет, {user.first_name}! Я ваш персональный Zero Bot.\n\n"
            f"**Доступные команды:**\n"
            f"• /start — Главное меню\n"
            f"• /help — Помощь\n"
            f"• /stats — Статистика\n\n"
            f"Просто напишите мне что-нибудь! 💬"
        )

    @client.on(events.NewMessage(pattern="/help"))
    async def help_handler(event):
        await event.respond(
            "🆘 **Помощь Zero Bot**\n\n"
            "Я умею:\n"
            "• 💬 Отвечать на сообщения\n"
            "• 🧠 Использовать навыки из маркетплейса\n"
            "• 🎛️ Настраиваться через Langflow\n"
            "• 📊 Показывать статистику\n\n"
            "Напишите что-нибудь, и я отвечу!"
        )

    @client.on(events.NewMessage(pattern="/stats"))
    async def stats_handler(event):
        await event.respond(
            "📊 **Статистика Zero Bot**\n\n"
            "💬 Сообщений обработано: 0\n"
            "🧠 Навыков установлено: 0\n"
            "⏱️ Аптайм: только что запущен\n"
            "🐳 Контейнер: standalone mode"
        )

    @client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith("/")))
    async def message_handler(event):
        msg = event.text.lower()
        _dbg("zero_bot:msg", "Message received", {"len": len(msg)}, "H4")
        if "привет" in msg:
            await event.respond("👋 Привет! Как дела?")
        elif "как дела" in msg:
            await event.respond("Отлично! Готов помочь 😊")
        elif "помощь" in msg or "help" in msg:
            await event.respond("Используйте /help для списка команд")
        else:
            await event.respond(f"🤔 Интересно! Вы написали: «{event.text}»\nЯ пока учусь — скоро смогу больше!")

    # --- Start ---

    try:
        _dbg("zero_bot:connect", "Connecting to Telegram...", hypothesis_id="H4")
        await client.start(bot_token=BOT_TOKEN)
        _dbg("zero_bot:connect", "Connected!", hypothesis_id="H4")

        me = await client.get_me()
        _dbg("zero_bot:me", "Bot identity", {"id": me.id, "username": me.username}, "H4")
        print(f"  Bot: @{me.username} (id: {me.id})")
        print(f"  RUNNING! Send /start to @{me.username}")
        print(f"  Press Ctrl+C to stop\n")

        _dbg("zero_bot:loop", "Entering run_until_disconnected", hypothesis_id="H4")
        await client.run_until_disconnected()

    except Exception as e:
        _dbg("zero_bot:error", str(e), {"type": type(e).__name__}, "H4")
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        _dbg("zero_bot:exit", "Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
