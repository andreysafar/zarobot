"""Telegram handlers for Zero Bot Instance."""

from telethon import events


async def handle_start(event, bot):
    sender = await event.get_sender()
    name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
    greeting = bot.personality.get_greeting(
        user_name=name,
        bot_name=bot.personality.display_name,
    )
    await event.respond(greeting)


async def handle_stats(event, bot):
    await event.respond(
        f"📊 **{bot.personality.display_name}**\n\n"
        f"Level: {bot.state.level}\n"
        f"XP: {bot.state.xp}\n"
        f"Messages: {bot.state.messages_total}\n"
        f"Created: {bot.state.created_at[:10]}"
    )


async def handle_help(event, bot):
    await event.respond(
        f"🤖 **{bot.personality.display_name}**\n\n"
        "Команды:\n"
        "/start — Приветствие\n"
        "/stats — Статистика бота\n"
        "/help — Помощь\n\n"
        "Просто пишите — я отвечу!"
    )


async def handle_message(event, bot):
    from loguru import logger
    sender = await event.get_sender()
    text = event.text
    try:
        response = await bot._process_message(text, sender)
        await event.respond(response)
        bot.state.add_xp(1)
    except Exception as e:
        logger.error("Message processing error: %s", e)
        if bot.personality.fallback:
            await event.respond(bot.personality.fallback)
