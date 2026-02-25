"""My bots and create-bot handlers."""

from telethon import Button, events


async def handle_my_bots(event, bot):
    """List user's bots."""
    user = await event.get_sender()
    bots = await bot.api.get_user_bots(user.id)
    if not bots:
        await event.edit(
            "🤖 **Мои боты**\n\n"
            "У вас пока нет ботов.\n"
            "Создайте своего первого бота! 🚀",
            buttons=[
                [Button.inline("➕ Создать бота", b"create_bot")],
                [Button.inline("🏪 Купить бота", b"marketplace_bots")],
                [Button.inline("⬅️ Назад", b"back_main")],
            ],
        )
        return
    bot_list = "🤖 **Ваши боты:**\n\n"
    buttons = []
    for b in bots:
        status_emoji = "🟢" if b["status"] == "active" else "🔴"
        bot_list += (
            f"{status_emoji} **{b['name']}**\n"
            f"📊 Уровень: {b['level']}\n"
            f"💬 Сообщений: {b['message_count']}\n"
            f"💰 Доход: {b['revenue']} IA-Coins\n\n"
        )
        buttons.append([Button.inline(f"⚙️ {b['name']}", f"manage_bot_{b['id']}".encode())])
    buttons.extend([
        [Button.inline("➕ Создать нового", b"create_bot")],
        [Button.inline("⬅️ Назад", b"back_main")],
    ])
    await event.edit(bot_list, buttons=buttons)


async def handle_create_bot(event, bot):
    """Create bot: open webapp."""
    import config
    webapp_url = f"{config.WEBAPP_URL}/create-bot"
    await event.edit(
        "🚀 **Создание Zero Bot**\n\n"
        "Создайте своего уникального бота за несколько минут!\n\n"
        "**Что вас ждет:**\n"
        "• 🎨 Выбор личности\n"
        "• 🧠 Настройка навыков\n"
        "• 🎛️ Langflow интеграция\n"
        "• 🔐 TON Wallet подключение\n\n"
        "Нажмите кнопку ниже для начала:",
        buttons=[
            [Button.url("🚀 Создать бота", webapp_url)],
            [Button.inline("⬅️ Назад", b"my_bots")],
        ],
    )
