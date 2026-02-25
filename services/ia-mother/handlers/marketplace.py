"""Marketplace: bots, skills, categories, install flow."""

from telethon import Button, events


async def handle_marketplace(event, bot):
    """Marketplace root menu."""
    await event.edit(
        "🏪 **Маркетплейс Zero Bot**\n\n"
        "Добро пожаловать в крупнейший маркетплейс ботов и навыков!\n\n"
        "Что вас интересует?",
        buttons=[
            [Button.inline("🤖 Боты", b"marketplace_bots")],
            [Button.inline("🧠 Навыки", b"marketplace_skills")],
            [Button.inline("👑 Личности", b"marketplace_personalities")],
            [Button.inline("🔥 Популярное", b"marketplace_trending")],
            [Button.inline("🔍 Поиск", b"marketplace_search")],
            [Button.inline("⬅️ Назад", b"back_main")],
        ],
    )


async def handle_marketplace_bots(event, bot):
    """Bots catalog."""
    bots = await bot.api.get_marketplace_bots()
    if not bots:
        await event.edit(
            "🤖 **Каталог ботов**\n\n"
            "Пока что ботов нет, но скоро они появятся!\n"
            "Создайте своего первого бота прямо сейчас! 🚀",
            buttons=[
                [Button.inline("➕ Создать бота", b"create_bot")],
                [Button.inline("⬅️ Назад", b"marketplace")],
            ],
        )
        return
    bot_list = "🤖 **Доступные боты:**\n\n"
    buttons = []
    for b in bots[:10]:
        bot_list += (
            f"**{b['name']}**\n"
            f"👤 {b['creator']}\n"
            f"💰 {b['price']} IA-Coins\n"
            f"⭐ {b['rating']}/5 ({b['reviews']} отзывов)\n\n"
        )
        buttons.append([Button.inline(f"🔍 {b['name']}", f"view_bot_{b['id']}".encode())])
    buttons.extend([
        [Button.inline("📄 Больше ботов", b"marketplace_bots_more")],
        [Button.inline("⬅️ Назад", b"marketplace")],
    ])
    await event.edit(bot_list, buttons=buttons)


async def handle_marketplace_skills(event, bot):
    """Skills catalog."""
    skills = await bot.api.get_marketplace_skills()
    skill_list = "🧠 **Доступные навыки:**\n\n"
    buttons = []
    for s in skills[:10]:
        skill_list += (
            f"**{s['name']}** v{s['version']}\n"
            f"📝 {s['description']}\n"
            f"🏷️ {s['category_name']} {s.get('category_icon', '')}\n"
            f"💰 {s['price_ia_coins']} IA-Coins"
            f"{' (Бесплатно)' if s['is_free'] else ''}\n"
            f"⭐ {s['average_rating']}/5 ({s['total_installations']} установок)\n"
            f"👨‍💻 {s['creator_name']}\n\n"
        )
        buttons.append([Button.inline(f"🔍 {s['name']}", f"view_skill_{s['id']}".encode())])
    buttons.extend([
        [Button.inline("🔍 Поиск навыков", b"search_skills")],
        [Button.inline("📂 По категориям", b"skills_categories")],
        [Button.inline("🔥 Популярные", b"skills_featured")],
        [Button.inline("➕ Создать навык", b"create_skill")],
        [Button.inline("⬅️ Назад", b"marketplace")],
    ])
    await event.edit(skill_list, buttons=buttons)


async def handle_skills_categories(event, bot):
    """Skill categories list."""
    categories = await bot.api.get_skill_categories()
    category_list = "📂 **Категории навыков:**\n\n"
    buttons = []
    for c in categories:
        category_list += f"{c['icon']} **{c['name']}**\n📊 {c['skills_count']} навыков\n\n"
        buttons.append([
            Button.inline(f"{c['icon']} {c['name']} ({c['skills_count']})", f"category_skills_{c['id']}".encode()),
        ])
    buttons.append([Button.inline("⬅️ Назад", b"marketplace_skills")])
    await event.edit(category_list, buttons=buttons)


async def handle_skills_featured(event, bot):
    """Featured skills."""
    skills = await bot.api.get_featured_skills()
    skill_list = "🔥 **Популярные навыки:**\n\n"
    buttons = []
    for i, s in enumerate(skills[:10], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}️⃣"
        skill_list += (
            f"{emoji} **{s['name']}**\n"
            f"📊 Популярность: {s['popularity_score']:.1f}/10\n"
            f"💰 {s['price_ia_coins']} IA-Coins\n"
            f"⭐ {s['average_rating']}/5 ({s['total_installations']} установок)\n\n"
        )
        buttons.append([Button.inline(f"{emoji} {s['name']}", f"view_skill_{s['id']}".encode())])
    buttons.append([Button.inline("⬅️ Назад", b"marketplace_skills")])
    await event.edit(skill_list, buttons=buttons)


async def handle_create_skill(event, bot):
    """Create skill: open webapp."""
    import config
    user = await event.get_sender()
    webapp_url = f"{config.WEBAPP_URL}/create-skill?user_id={user.id}"
    await event.edit(
        "🛠️ **Создание навыка**\n\n"
        "Создайте свой уникальный навык для Zero Bot!\n\n"
        "**Что вас ждет:**\n"
        "• 🎨 Выбор категории и настройка\n"
        "• 💻 Загрузка кода или API endpoint\n"
        "• 🔧 Конфигурация параметров\n"
        "• 💰 Установка цены в IA-Coins\n"
        "• 🚀 Публикация в маркетплейс\n\n"
        "**Доходы создателя:**\n"
        "• 60% от продаж навыка\n"
        "• 30% платформе Zero Bot\n"
        "• 10% Telegram за Stars\n\n"
        "Нажмите кнопку для начала:",
        buttons=[
            [Button.url("🛠️ Создать навык", webapp_url)],
            [Button.inline("📚 Документация API", b"skill_docs")],
            [Button.inline("⬅️ Назад", b"marketplace_skills")],
        ],
    )


async def handle_view_skill(event, bot):
    """Single skill details."""
    skill_id = event.pattern_match.group(1).decode()
    skill = await bot.api.get_skill_details(skill_id)
    if not skill:
        await event.answer("Навык не найден", alert=True)
        return
    skill_info = (
        f"🧠 **{skill['name']}** v{skill['version']}\n\n"
        f"📝 **Описание:**\n{skill['description']}\n\n"
        f"🏷️ **Категория:** {skill['category_name']} {skill.get('category_icon', '')}\n"
        f"👨‍💻 **Создатель:** {skill['creator_name']}\n"
        f"💰 **Цена:** {skill['price_ia_coins']} IA-Coins"
        f"{' (Бесплатно)' if skill['is_free'] else ''}\n"
        f"⭐ **Рейтинг:** {skill['average_rating']}/5 ({skill['ratings_count']} оценок)\n"
        f"📊 **Установки:** {skill['total_installations']}\n"
        f"🔥 **Популярность:** {skill['popularity_score']:.1f}/10\n\n"
        f"🛠️ **Тип:** {skill['execution_type']}\n"
        f"🏷️ **Теги:** {', '.join(skill['tags'])}\n\n"
        f"📅 **Создан:** {skill['created_at'][:10]}\n"
    )
    if skill.get("requirements"):
        skill_info += f"⚠️ **Требования:** {', '.join(skill['requirements'])}\n"
    buttons = [
        [Button.inline("💾 Установить навык", f"install_skill_{skill_id}".encode())],
        [
            Button.inline("⭐ Оценить", f"rate_skill_{skill_id}".encode()),
            Button.inline("💬 Отзывы", f"skill_reviews_{skill_id}".encode()),
        ],
        [Button.inline("📊 Статистика", f"skill_stats_{skill_id}".encode())],
        [Button.inline("⬅️ Назад", b"marketplace_skills")],
    ]
    await event.edit(skill_info, buttons=buttons)


async def handle_install_skill(event, bot):
    """Choose bot to install skill on."""
    skill_id = event.pattern_match.group(1).decode()
    user = await event.get_sender()
    user_bots = await bot.api.get_user_bots(user.id)
    if not user_bots:
        await event.edit(
            "🤖 **Установка навыка**\n\n"
            "У вас нет ботов для установки навыка.\n"
            "Сначала создайте бота!",
            buttons=[
                [Button.inline("➕ Создать бота", b"create_bot")],
                [Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())],
            ],
        )
        return
    bot_list = "🤖 **Выберите бота для установки навыка:**\n\n"
    buttons = []
    for b in user_bots[:10]:
        status_emoji = "🟢" if b["status"] == "active" else "🔴"
        bot_list += f"{status_emoji} **{b['name']}** (Уровень {b['level']})\n"
        buttons.append([
            Button.inline(f"{status_emoji} {b['name']}", f"confirm_install_{skill_id}_{b['id']}".encode()),
        ])
    buttons.append([Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())])
    await event.edit(bot_list, buttons=buttons)


async def handle_confirm_install(event, bot):
    """Confirm skill install on bot."""
    skill_id = event.pattern_match.group(1).decode()
    bot_id = event.pattern_match.group(2).decode()
    skill = await bot.api.get_skill_details(skill_id)
    bot_details = await bot.api.get_bot_details(bot_id)
    if not skill or not bot_details:
        await event.answer("Данные не найдены", alert=True)
        return
    confirm_text = (
        f"💾 **Подтверждение установки**\n\n"
        f"🧠 **Навык:** {skill['name']} v{skill['version']}\n"
        f"🤖 **Бот:** {bot_details['name']}\n"
        f"💰 **Цена:** {skill['price_ia_coins']} IA-Coins\n\n"
        f"После установки навык будет доступен в вашем боте.\n"
        f"Вы сможете настроить его параметры в панели управления.\n\n"
        f"Продолжить установку?"
    )
    buttons = [
        [Button.inline("✅ Установить", f"process_install_{skill_id}_{bot_id}".encode())],
        [Button.inline("⬅️ Отмена", f"install_skill_{skill_id}".encode())],
    ]
    await event.edit(confirm_text, buttons=buttons)


async def handle_process_install(event, bot):
    """Execute skill install."""
    from loguru import logger
    skill_id = event.pattern_match.group(1).decode()
    bot_id = event.pattern_match.group(2).decode()
    user = await event.get_sender()
    try:
        result = await bot.api.install_skill_on_bot(skill_id=skill_id, bot_id=bot_id, user_id=user.id)
        if result["success"]:
            await event.edit(
                f"✅ **Навык успешно установлен!**\n\n"
                f"🧠 **Навык:** {result['skill_name']}\n"
                f"🤖 **Бот:** {result['bot_name']}\n"
                f"💰 **Оплачено:** {result['price_paid']} IA-Coins\n"
                f"📋 **ID установки:** {result['installation_id']}\n\n"
                f"Навык активен и готов к использованию!\n"
                f"Настройте его в панели управления ботом.",
                buttons=[
                    [Button.inline("⚙️ Управление ботом", f"manage_bot_{bot_id}".encode())],
                    [Button.inline("🏪 Продолжить покупки", b"marketplace_skills")],
                ],
            )
        else:
            await event.edit(
                f"❌ **Ошибка установки**\n\n"
                f"Причина: {result['error']}\n\n"
                f"Попробуйте еще раз или обратитесь в поддержку.",
                buttons=[
                    [Button.inline("🔄 Повторить", f"process_install_{skill_id}_{bot_id}".encode())],
                    [Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())],
                ],
            )
    except Exception as e:
        logger.error(f"Ошибка установки навыка: {e}")
        await event.edit(
            "❌ **Техническая ошибка**\n\n"
            "Не удалось установить навык.\n"
            "Попробуйте позже или обратитесь в поддержку.",
            buttons=[[Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())]],
        )
