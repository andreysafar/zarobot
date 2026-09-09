"""Telegram handlers for Zero Bot Instance.

Command dispatch is centralised in `handle_builtin_command`; the bot instance
calls it only after the skill chain has had a chance to claim the command.
"""

from loguru import logger

# Commands handled by the runtime itself (skills get first refusal).
BUILTIN_COMMANDS = {"start", "stats", "help", "reset", "bug", "cancel"}

COMMAND_HELP = {
    "/start": "Greeting",
    "/stats": "Bot statistics",
    "/reset": "Reset conversation history",
    "/bug": "Report a bug",
    "/help": "This help",
}


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
        f"Created: {bot.state.created_at[:10]}\n"
        f"Bot ID: `{bot.state.file.parent.name}`"
    )


async def handle_help(event, bot):
    lines = "\n".join(f"{cmd} — {desc}" for cmd, desc in COMMAND_HELP.items())
    skill_commands = ""
    if bot.skills.command_names:
        listed = "\n".join(f"/{name.lstrip('/')}" for name in bot.skills.command_names)
        skill_commands = f"\n\nSkill commands:\n{listed}"
    await event.respond(
        f"🤖 **{bot.personality.display_name}**\n\n"
        f"Commands:\n{lines}"
        f"{skill_commands}"
    )


async def handle_reset(event, bot):
    """Reset conversation history for this chat (or user, in DM)."""
    chat_id = getattr(event, "chat_id", None)
    sender = await event.get_sender()
    key = chat_id if chat_id else getattr(sender, "id", 0)
    bot.conversations.clear_history(key)
    await event.respond("🔄 Conversation history cleared. Fresh start!")


async def handle_bug(event, bot):
    """Bug report flow — ask user to describe the issue."""
    sender = await event.get_sender()
    await event.respond(
        "🐛 **Bug Report**\n\n"
        "Describe the issue you encountered.\n"
        "Include:\n"
        "• What you were doing\n"
        "• What happened\n"
        "• What you expected\n\n"
        "Send /cancel to abort."
    )
    # Store state for next message
    bot._bug_report_user = getattr(sender, "id", 0)


async def handle_cancel(event, bot):
    """Abort the pending bug report, if any."""
    sender = await event.get_sender()
    if getattr(bot, "_bug_report_user", None) == getattr(sender, "id", 0):
        bot._bug_report_user = None
        await event.respond("❌ Bug report cancelled.")
    else:
        await event.respond("Nothing to cancel.")


async def handle_builtin_command(event, bot, command: str, args: str) -> None:
    """Dispatch a built-in command. Unknown commands are silently ignored in
    groups so several bots can coexist; in DMs we show help."""
    handler = {
        "start": handle_start,
        "stats": handle_stats,
        "help": handle_help,
        "reset": handle_reset,
        "bug": handle_bug,
        "cancel": handle_cancel,
    }.get(command)

    if handler is None:
        if getattr(event, "is_private", False):
            await event.respond(
                f"Неизвестная команда `/{command}`. Отправьте /help.",
            )
        return

    await handler(event, bot)
    bot.state.add_xp(1)


async def handle_message(event, bot, text: str = None):
    """Main message handler — process addressed messages through the LLM."""
    sender = await event.get_sender()
    text = text if text is not None else event.text
    user_id = getattr(sender, "id", 0)

    # Check if this is a bug report response
    if getattr(bot, "_bug_report_user", None) == user_id:
        bot._bug_report_user = None
        if text.strip().lower() == "/cancel":
            await event.respond("❌ Bug report cancelled.")
            return
        await bot.core_api.submit_bug(
            user_id=user_id,
            title=f"Bug from {getattr(sender, 'first_name', 'User')}",
            description=text,
        )
        await event.respond("✅ Bug report submitted. Thank you!")
        return

    chat_id = getattr(event, "chat_id", None) or 0
    try:
        response = await bot._process_message(text, sender, chat_id=chat_id)
        await event.respond(response)
        bot.state.add_xp(1)
    except Exception as e:
        logger.error("Message processing error: {}", e)
        await bot.core_api.report_error(
            bot_id=bot.BOT_ID,
            user_id=user_id,
            error_type="message_error",
            message=str(e),
            traceback_str=__import__("traceback").format_exc(),
            context={"message_text": text[:200]},
        )
        fallback = bot.personality.fallback or "Sorry, something went wrong. Please try again."
        await event.respond(fallback)
