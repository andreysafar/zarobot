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
        # Рейтингов у ботов пока нет ни в модели, ни в API — не показываем то,
        # чего не существует. .get() держит экран живым, если поле пропало.
        bot_list += (
            f"**{b['name']}**\n"
            f"👤 {b.get('creator', '—')}\n"
            f"💰 {b.get('price', 0)} IA-Coins\n"
            f"📊 Уровень {b.get('level', 0)}\n\n"
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


async def handle_marketplace_personalities(event, bot):
    """Personalities catalog (placeholder)."""
    await event.edit(
        "👑 **Личности**\n\n"
        "Скоро здесь появятся уникальные личности для ваших ботов!\n\n"
        "Доступные личности:\n"
        "• 🤖 **Ия** — дружелюбный AI-ассистент (бесплатно)\n",
        buttons=[
            [Button.inline("⬅️ Назад", b"marketplace")],
        ],
    )


async def handle_marketplace_trending(event, bot):
    """Trending items."""
    await event.edit(
        "🔥 **Тренды Zero Bot**\n\n"
        "📊 **Популярные навыки:**\n"
        "1. Умный переводчик — 342 установок\n"
        "2. Генерация кода Python — 156 установок\n"
        "3. Анализ настроения — 89 установок\n\n"
        "🤖 **Популярные боты:**\n"
        "Скоро здесь появятся боты!\n",
        buttons=[
            [Button.inline("🧠 Навыки", b"marketplace_skills")],
            [Button.inline("🤖 Боты", b"marketplace_bots")],
            [Button.inline("⬅️ Назад", b"marketplace")],
        ],
    )


async def handle_marketplace_search(event, bot):
    """Search in marketplace."""
    await event.edit(
        "🔍 **Поиск**\n\n"
        "Введите запрос для поиска навыков, ботов или личностей.\n\n"
        "Примеры:\n"
        "• `переводчик` — найти навыки перевода\n"
        "• `python` — найти навыки для разработки\n"
        "• `анализ` — найти аналитические навыки",
        buttons=[[Button.inline("⬅️ Назад", b"marketplace")]],
    )


async def handle_view_bot(event, bot):
    """Single bot details."""
    bot_id = event.pattern_match.group(1).decode()
    bot_data = await bot.api.get_bot_details(bot_id)
    if not bot_data:
        await event.answer("Бот не найден", alert=True)
        return

    text = (
        f"🤖 **{bot_data['name']}**\n\n"
        f"👤 **Владелец:** {bot_data.get('owner_telegram', 'Unknown')}\n"
        f"📊 **Уровень:** {bot_data.get('level', 0)}\n"
        f"🧬 **Личность:** {bot_data.get('personality', 'default')}\n"
    )
    if bot_data.get("nft_address"):
        text += f"🎫 **NFT:** `{bot_data['nft_address'][:16]}...`\n"
    if bot_data.get("container_id"):
        text += f"🐳 **Контейнер:** `{bot_data['container_id'][:12]}...`\n"

    buttons = [
        [Button.inline("💰 Купить бота", f"buy_bot_{bot_id}".encode())],
        [Button.inline("⬅️ Назад", b"marketplace_bots")],
    ]
    await event.edit(text, buttons=buttons)


async def handle_buy_bot(event, bot):
    """Buy a bot from marketplace."""
    bot_id = event.pattern_match.group(1).decode()
    user = await event.get_sender()

    await event.edit(
        f"💰 **Покупка бота**\n\n"
        f"Подтвердите покупку.\n"
        f"Стоимость: 50 IA-Coins\n"
        f"Вы получите полную копию бота с его личностью и навыками.\n",
        buttons=[
            [Button.inline("✅ Купить", f"confirm_buy_bot_{bot_id}".encode())],
            [Button.inline("❌ Отмена", f"view_bot_{bot_id}".encode())],
        ],
    )


async def handle_confirm_buy_bot(event, bot):
    """Confirm bot purchase."""
    from loguru import logger
    bot_id = event.pattern_match.group(1).decode()
    user = await event.get_sender()

    try:
        # Call Core API to buy bot
        result = await bot.api._request(
            "POST",
            f"/api/v1/marketplace/bots/{bot_id}/buy/",
            json={"buyer_id": user.id},
        )
        if result.get("success"):
            # Владение сменилось в базе, но контейнер всё ещё крутится со
            # старым OWNER_ID — без пересоздания прежний владелец остался бы
            # админом проданного бота.
            handover = "\n"
            try:
                from docker_manager import BotContainerManager

                owner_telegram = f"@{user.username}" if user.username else str(user.id)
                moved = await BotContainerManager().reassign_owner(
                    bot_id, user.id, owner_telegram
                )
                if not moved.get("success"):
                    logger.error(
                        "Не удалось передать контейнер бота {}: {}",
                        bot_id, moved.get("error"),
                    )
                    handover = (
                        "\n⚠️ Права в базе переданы, но контейнер не перезапущен.\n"
                        "Обратитесь к администратору.\n"
                    )
            except Exception as e:
                logger.error("Ошибка передачи контейнера {}: {}", bot_id, e)
                handover = (
                    "\n⚠️ Права в базе переданы, но контейнер не перезапущен.\n"
                    "Обратитесь к администратору.\n"
                )

            await event.edit(
                f"🎉 **Бот куплен!**\n\n"
                f"Вы стали владельцем нового бота.\n"
                f"{handover}"
                f"Перейдите в 'Мои боты' для управления.",
                buttons=[
                    [Button.inline("🤖 Мои боты", b"my_bots")],
                    [Button.inline("🏠 Главная", b"back_main")],
                ],
            )
        else:
            await event.edit(
                f"❌ Ошибка: {result.get('error', 'Unknown error')}",
                buttons=[[Button.inline("⬅️ Назад", b"marketplace_bots")]],
            )
    except Exception as e:
        logger.error(f"Bot purchase failed: {e}")
        await event.edit(
            "❌ Ошибка при покупке. Попробуйте позже.",
            buttons=[[Button.inline("⬅️ Назад", b"marketplace_bots")]],
        )
