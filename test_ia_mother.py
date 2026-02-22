#!/usr/bin/env python3
"""
Standalone IA-Mother bot — no Django, no Redis, no FastAPI.
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
        f.write(json.dumps({"id": f"log_{int(datetime.now().timestamp()*1000)}", "timestamp": int(datetime.now().timestamp()*1000), "location": loc, "message": msg, "data": data or {}, "runId": "ia_mother_run", "hypothesisId": hypothesis_id or ""}) + "\n")
    # #endregion

API_ID = 25039464
API_HASH = "9ebe53a317b075a5eb7f8ea577f7f733"
BOT_TOKEN = "7312496733:AAGkY8KzYeQt3ysjv0fW81fU_Zsjem8hLs4"

from telethon import TelegramClient, events, Button

async def main():
    _dbg("test_ia_mother:main", "Starting", {"api_id": API_ID, "token_prefix": BOT_TOKEN[:15]}, "H1")
    print(f"Starting IA-Mother bot...")
    print(f"  API ID: {API_ID}")
    print(f"  Token:  {BOT_TOKEN[:15]}...")

    client = TelegramClient("ia_mother_session", API_ID, API_HASH)

    # --- Handlers ---

    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        _dbg("ia_mother:start_handler", "/start received", {"sender": event.sender_id}, "H2")
        buttons = [
            [Button.inline("🏪 Маркетплейс", b"marketplace")],
            [Button.inline("💱 Обменник", b"exchange")],
            [Button.inline("🤖 Мои боты", b"my_bots")],
            [Button.inline("📊 Статистика", b"stats")],
            [Button.inline("ℹ️ Помощь", b"help")]
        ]
        await event.respond(
            "🤖 **IA-Mother** — Ваш проводник в мир Zero Bot!\n\n"
            "🏪 **Маркетплейс ботов и навыков**\n"
            "💱 **Обменник Stars ↔ IA-Coins**\n"
            "📊 **Аналитика и статистика**\n\n"
            "Выберите действие:",
            buttons=buttons
        )

    @client.on(events.CallbackQuery(pattern=b"marketplace"))
    async def marketplace_handler(event):
        await event.edit(
            "🏪 **Маркетплейс Zero Bot**\n\n"
            "Добро пожаловать в крупнейший маркетплейс ботов и навыков!\n\n"
            "Что вас интересует?",
            buttons=[
                [Button.inline("🤖 Боты", b"marketplace_bots")],
                [Button.inline("🧠 Навыки", b"marketplace_skills")],
                [Button.inline("👑 Личности", b"marketplace_personalities")],
                [Button.inline("🔥 Популярное", b"marketplace_trending")],
                [Button.inline("⬅️ Назад", b"back_main")]
            ]
        )

    @client.on(events.CallbackQuery(pattern=b"marketplace_skills"))
    async def skills_handler(event):
        await event.edit(
            "🧠 **Доступные навыки:**\n\n"
            "**Генератор Python кода** v2.1.0\n"
            "📝 Автоматическая генерация Python кода с AI\n"
            "💰 25 IA-Coins | ⭐ 4.7/5 | 📊 156 установок\n\n"
            "**Умный переводчик Pro** v3.0.2\n"
            "📝 Перевод 50+ языков с контекстом\n"
            "💰 18 IA-Coins | ⭐ 5.0/5 | 📊 342 установки\n\n"
            "**Анализ настроения** v1.0.0\n"
            "📝 Определение эмоций в тексте\n"
            "💰 Бесплатно | ⭐ 4.3/5 | 📊 89 установок\n",
            buttons=[
                [Button.inline("🔍 Поиск", b"search_skills")],
                [Button.inline("📂 Категории", b"skills_categories")],
                [Button.inline("➕ Создать навык", b"create_skill")],
                [Button.inline("⬅️ Назад", b"marketplace")]
            ]
        )

    @client.on(events.CallbackQuery(pattern=b"marketplace_bots"))
    async def bots_handler(event):
        await event.edit(
            "🤖 **Доступные боты:**\n\n"
            "**Помощник Программиста**\n"
            "👤 @developer123 | 💰 50 IA-Coins | ⭐ 4.8/5\n\n"
            "**Учитель Английского**\n"
            "👤 @teacher_ai | 💰 30 IA-Coins | ⭐ 4.9/5\n\n"
            "**Финансовый Аналитик**\n"
            "👤 @fintech_bot | 💰 75 IA-Coins | ⭐ 4.6/5\n",
            buttons=[
                [Button.inline("➕ Создать бота", b"create_bot")],
                [Button.inline("⬅️ Назад", b"marketplace")]
            ]
        )

    @client.on(events.CallbackQuery(pattern=b"exchange"))
    async def exchange_handler(event):
        await event.edit(
            "💱 **Обменник IA-Mother**\n\n"
            "**Ваш баланс:**\n"
            "⭐ 1000 Stars\n"
            "🪙 10.50 IA-Coins\n\n"
            "**Текущие курсы:**\n"
            "1 Star = 0.01 IA-Coin\n"
            "1 IA-Coin = 100 Stars\n\n"
            "Что хотите обменять?",
            buttons=[
                [Button.inline("⭐→🪙 Stars → IA-Coins", b"exchange_s2i")],
                [Button.inline("🪙→⭐ IA-Coins → Stars", b"exchange_i2s")],
                [Button.inline("⬅️ Назад", b"back_main")]
            ]
        )

    @client.on(events.CallbackQuery(pattern=b"stats"))
    async def stats_handler(event):
        await event.edit(
            "📊 **Статистика Zero Bot**\n\n"
            "🤖 **Боты:** 1,247\n"
            "👥 **Пользователи:** 5,892\n"
            "🧠 **Навыки:** 156\n"
            "👑 **Личности:** 89\n\n"
            "💰 **Экономика:**\n"
            "🪙 IA-Coins в обороте: 1,250,000\n"
            "💎 NFT Паспортов: 1,247\n"
            "💸 Объем торгов: 45,892 IA-Coins",
            buttons=[[Button.inline("⬅️ Назад", b"back_main")]]
        )

    @client.on(events.CallbackQuery(pattern=b"help"))
    async def help_handler(event):
        await event.edit(
            "ℹ️ **Помощь IA-Mother**\n\n"
            "🏪 **Маркетплейс** — покупка/продажа ботов и навыков\n"
            "💱 **Обменник** — конвертация Stars ↔ IA-Coins\n"
            "🤖 **Мои боты** — управление вашими ботами\n"
            "📊 **Статистика** — аналитика платформы\n\n"
            "🔗 Каждый бот = отдельный Docker-контейнер\n"
            "🧠 Навыки регистрируются в Solana\n"
            "💰 Оплата через IA-Coins (dual-chain TON+Solana)",
            buttons=[[Button.inline("⬅️ Назад", b"back_main")]]
        )

    @client.on(events.CallbackQuery(pattern=b"back_main"))
    async def back_handler(event):
        await start_handler(event)

    @client.on(events.CallbackQuery)
    async def fallback_callback(event):
        data = event.data.decode() if event.data else "unknown"
        if data not in ("marketplace", "exchange", "stats", "help", "back_main",
                        "marketplace_bots", "marketplace_skills", "marketplace_personalities",
                        "marketplace_trending", "search_skills", "skills_categories",
                        "create_skill", "create_bot", "my_bots", "exchange_s2i", "exchange_i2s"):
            await event.answer(f"🔧 '{data}' — в разработке", alert=False)

    # --- Start ---

    try:
        _dbg("ia_mother:connect", "Connecting to Telegram...", hypothesis_id="H1")
        await client.start(bot_token=BOT_TOKEN)
        _dbg("ia_mother:connect", "Connected!", hypothesis_id="H1")

        me = await client.get_me()
        _dbg("ia_mother:me", "Bot identity", {"id": me.id, "username": me.username}, "H1")
        print(f"  Bot: @{me.username} (id: {me.id})")
        print(f"  RUNNING! Send /start to @{me.username}")
        print(f"  Press Ctrl+C to stop\n")

        _dbg("ia_mother:loop", "Entering run_until_disconnected", hypothesis_id="H2")
        await client.run_until_disconnected()

    except Exception as e:
        _dbg("ia_mother:error", str(e), {"type": type(e).__name__}, "H1")
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        _dbg("ia_mother:exit", "Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
