"""Start menu and back-to-main handlers."""

from telethon import Button, events

import config

config._dbg("handlers.start:module", "Module loaded", hyp="H2")


async def handle_start(event, bot):
    """Main menu IA-Mother."""
    config._dbg("handlers.start:start", "/start received", {"sender_id": event.sender_id}, "H2")
    welcome_msg = (
        "🤖 **IA-Mother** - Ваш проводник в мир Zero Bot!\n\n"
        "🏪 **Маркетплейс ботов и навыков**\n"
        "💱 **Обменник Stars ↔ IA-Coins**\n"
        "📊 **Аналитика и статистика**\n\n"
        "Выберите действие:"
    )
    buttons = [
        [Button.inline("🏪 Маркетплейс", b"marketplace")],
        [Button.inline("💱 Обменник", b"exchange")],
        [Button.inline("🤖 Мои боты", b"my_bots")],
        [Button.inline("📊 Статистика", b"stats")],
        [Button.inline("ℹ️ Помощь", b"help")],
    ]
    await event.respond(welcome_msg, buttons=buttons)


async def handle_back_main(event, bot):
    """Return to main menu."""
    await handle_start(event, bot)
