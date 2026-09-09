"""My bots and create-bot handlers — real Docker container management."""

import uuid
from typing import TYPE_CHECKING
from telethon import Button, events
from loguru import logger

import config


def _states(bot) -> dict:
    """Состояния создания бота, по одному на пользователя."""
    if not hasattr(bot, "_create_bot_states"):
        bot._create_bot_states = {}
    return bot._create_bot_states


def get_create_state(bot, user_id: int) -> dict | None:
    """Состояние мастера для пользователя — им роутер выбирает шаг."""
    return _states(bot).get(user_id)

if TYPE_CHECKING:
    from bot import IAMotherBot


async def handle_my_bots(event, bot):
    """List user's bots with real container status."""
    user = await event.get_sender()

    # Get bots from Core API
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
            f"📊 Уровень: {b['level']} | XP: {b.get('xp', 0)}\n"
            f"💬 Сообщений: {b.get('message_count', '0')}\n"
            f"🧩 Навыков: {b.get('skills_count', 0)}\n"
        )
        if b.get("nft_address"):
            bot_list += f"🎫 NFT: `{b['nft_address'][:12]}...`\n"
        bot_list += "\n"
        buttons.append([Button.inline(f"⚙️ {b['name']}", f"manage_bot_{b['id']}".encode())])

    buttons.extend([
        [Button.inline("➕ Создать нового", b"create_bot")],
        [Button.inline("⬅️ Назад", b"back_main")],
    ])
    await event.edit(bot_list, buttons=buttons)


async def handle_create_bot(event, bot):
    """
    Create bot flow:
    1. Ask for bot name
    2. Ask for bot token (from BotFather)
    3. Create BotPassport in Core API
    4. Spawn Docker container
    5. Done!

    NFT minting is not part of this flow: the on-chain mint is unimplemented.
    """
    user = await event.get_sender()

    if not config.can_create_bots(user.id):
        await event.edit(
            "⛔ Создание ботов на этом сервере ограничено.\n\n"
            "Обратитесь к администратору платформы.",
            buttons=[[Button.inline("⬅️ Назад", b"my_bots")]],
        )
        return

    # Step 1: Ask for bot name
    await event.edit(
        "🚀 **Создание Zero Bot**\n\n"
        "Шаг 1/3: Введите имя для вашего бота.\n\n"
        "Имя будет отображаться в Telegram и в маркетплейсе.\n"
        "Пример: `Мой Помощник`, `Алиса`, `CodeBot`",
        buttons=[[Button.inline("❌ Отмена", b"my_bots")]],
    )

    # Store state for next step
    # Ключуем по пользователю: один общий атрибут означал, что два человека,
    # создающих бота одновременно, затирают состояние друг друга — включая
    # чужой токен от BotFather.
    _states(bot)[user.id] = {
        "user_id": user.id,
        "user_telegram": f"@{user.username}" if user.username else str(user.id),
        "step": 1,
    }


async def handle_create_bot_name(event, bot):
    """Handle bot name input (step 2)."""
    sender = await event.get_sender()
    state = _states(bot).get(getattr(sender, "id", 0))
    if state is None:
        return

    text = event.text.strip()
    if len(text) < 2 or len(text) > 50:
        await event.respond("❌ Имя должно быть от 2 до 50 символов. Попробуйте ещё раз:")
        return

    state["bot_name"] = text
    state["step"] = 2

    await event.respond(
        f"✅ Отлично! Имя: **{text}**\n\n"
        "Шаг 2/3: Отправьте токен бота от @BotFather.\n\n"
        "Если у вас ещё нет бота:\n"
        "1. Откройте @BotFather в Telegram\n"
        "2. Нажмите /newbot\n"
        "3. Следуйте инструкциям\n"
        "4. Скопируйте и отправьте токен сюда\n\n"
        "Пример: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`",
        buttons=[[Button.inline("❌ Отмена", b"my_bots")]],
    )


async def handle_create_bot_token(event, bot):
    """Handle bot token input (step 3 — create everything)."""
    sender = await event.get_sender()
    user_id = getattr(sender, "id", 0)
    state = _states(bot).get(user_id)
    if state is None or state.get("step") != 2:
        return

    text = event.text.strip()

    # Basic token validation
    if ":" not in text or len(text) < 20:
        await event.respond("❌ Неверный формат токена. Должен быть вида `123456:ABCdef...`")
        return

    state["bot_token"] = text
    state["step"] = 3

    # NFT-паспорт пока не выпускается: минт в ton_client не реализован.
    # Обещать его в интерфейсе — врать пользователю.
    await event.respond("⏳ Создаю вашего бота...\n\n"
                       "• Создание паспорта бота\n"
                       "• Запуск контейнера\n")

    try:
        # Step 1: Create BotPassport in Core API
        passport_data = await bot.api.create_passport(
            owner_id=state["user_id"],
            owner_telegram=state["user_telegram"],
            name=state["bot_name"],
        )
        bot_id = passport_data["id"]
        logger.info(f"Bot passport created: {bot_id}")

        # Step 2: Spawn Docker container
        from docker_manager import BotContainerManager
        container_mgr = BotContainerManager()

        container_result = await container_mgr.spawn_bot(
            owner_id=state["user_id"],
            owner_telegram=state["user_telegram"],
            bot_name=state["bot_name"],
            bot_token=state["bot_token"],
        )

        if not container_result.get("success"):
            logger.error(f"Container spawn failed: {container_result.get('error')}")
            await event.respond(
                f"❌ Ошибка при создании контейнера:\n{container_result.get('error')}\n\n"
                "Паспорт бота создан, но контейнер не запущен. Попробуйте позже."
            )
            return

        # Step 3: Update Core API with container ID
        await bot.api.update_bot_container(bot_id, container_result["container_id"])

        # Cleanup state
        _states(bot).pop(user_id, None)

        await event.respond(
            f"🎉 **Бот создан!**\n\n"
            f"Имя: **{state['bot_name']}**\n"
            f"ID: `{bot_id}`\n"
            f"Контейнер: `{container_result['container_id'][:12]}...`\n\n"
            "Бот запущен и готов к работе!\n"
            "Отправьте ему /start в Telegram.",
            buttons=[
                [Button.inline("📋 Мои боты", b"my_bots")],
                [Button.inline("🏠 Главная", b"back_main")],
            ],
        )

    except Exception as e:
        logger.error(f"Bot creation failed: {e}")
        await event.respond(
            f"❌ Ошибка при создании бота: {str(e)}\n\n"
            "Попробуйте ещё раз или обратитесь в поддержку.",
            buttons=[[Button.inline("⬅️ Назад", b"my_bots")]],
        )


async def handle_manage_bot(event, bot, bot_id: str):
    """Bot management panel."""
    status = await bot.api.get_bot_status(bot_id)
    if not status:
        await event.edit("❌ Бот не найден", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])
        return

    status_emoji = "🟢" if status.get("status") == "active" else "🔴"
    text = (
        f"{status_emoji} **Управление ботом**\n\n"
        f"Имя: {status.get('name', 'Unknown')}\n"
        f"Статус: {status.get('status', 'unknown')}\n"
        f"Уровень: {status.get('level', 0)}\n"
        f"XP: {status.get('xp', 0)}\n"
    )
    if status.get("nft_address"):
        text += f"🎫 NFT: `{status['nft_address'][:16]}...`\n"
    if status.get("container_id"):
        text += f"🐳 Container: `{status['container_id'][:12]}...`\n"

    await event.edit(text, buttons=[
        [Button.inline("🔄 Перезапустить", f"restart_bot_{bot_id}".encode())],
        [Button.inline("⏸️ Остановить", f"stop_bot_{bot_id}".encode())],
        [Button.inline("▶️ Запустить", f"start_bot_{bot_id}".encode())],
        [Button.inline("🗑️ Удалить", f"delete_bot_{bot_id}".encode())],
        [Button.inline("📋 Логи", f"logs_bot_{bot_id}".encode())],
        [Button.inline("⬅️ Назад", b"my_bots")],
    ])


async def handle_restart_bot(event, bot, bot_id: str):
    """Restart bot container."""
    from docker_manager import BotContainerManager
    mgr = BotContainerManager()
    success = await mgr.restart_bot(bot_id)
    if success:
        await event.respond("✅ Бот перезапущен!", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])
    else:
        await event.respond("❌ Ошибка при перезапуске", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])


async def handle_stop_bot(event, bot, bot_id: str):
    """Stop bot container."""
    from docker_manager import BotContainerManager
    mgr = BotContainerManager()
    success = await mgr.stop_bot(bot_id)
    if success:
        await event.respond("✅ Бот остановлен (sleep mode)", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])
    else:
        await event.respond("❌ Ошибка при остановке", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])


async def handle_start_bot(event, bot, bot_id: str):
    """Start bot container."""
    from docker_manager import BotContainerManager
    mgr = BotContainerManager()
    success = await mgr.start_bot(bot_id)
    if success:
        await event.respond("✅ Бот запущен!", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])
    else:
        await event.respond("❌ Ошибка при запуске", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])


async def handle_delete_bot(event, bot, bot_id: str):
    """Delete bot container (with confirmation)."""
    await event.edit(
        "⚠️ **Удалить бота?**\n\n"
        "Это действие нельзя отменить.\n"
        "Контейнер будет удалён, NFT-паспорт останется у вас.",
        buttons=[
            [Button.inline("🗑️ Да, удалить", f"confirm_delete_{bot_id}".encode())],
            [Button.inline("❌ Отмена", f"manage_bot_{bot_id}".encode())],
        ],
    )


async def handle_confirm_delete_bot(event, bot, bot_id: str):
    """Confirm bot deletion."""
    from docker_manager import BotContainerManager
    mgr = BotContainerManager()
    success = await mgr.destroy_bot(bot_id)
    if success:
        await event.respond("✅ Бот удалён!", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])
    else:
        await event.respond("❌ Ошибка при удалении", buttons=[[Button.inline("⬅️ Назад", b"my_bots")]])


async def handle_bot_logs(event, bot, bot_id: str):
    """Show bot container logs."""
    from docker_manager import BotContainerManager
    mgr = BotContainerManager()
    logs = await mgr.get_bot_logs(bot_id, tail=50)
    # Truncate for Telegram (max 4096 chars)
    if len(logs) > 3000:
        logs = "...\n" + logs[-3000:]
    await event.edit(
        f"📋 **Логи бота {bot_id}:**\n\n```{logs}```",
        buttons=[[Button.inline("⬅️ Назад", f"manage_bot_{bot_id}".encode())]],
    )
