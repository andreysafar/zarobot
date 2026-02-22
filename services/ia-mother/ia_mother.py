"""
IA-Mother Bot - Маркетплейс ботов и навыков + Обменник Stars ↔ IA-Coins
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
from pathlib import Path

import httpx
from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from loguru import logger

# #region agent log
_DBG_LOG = str(Path(__file__).resolve().parent.parent.parent / ".cursor" / "debug.log")
def _dbg(loc, msg, data=None, hyp=None):
    import json as _j, os as _o
    _o.makedirs(_o.path.dirname(_DBG_LOG), exist_ok=True)
    with open(_DBG_LOG, "a") as _f:
        _f.write(_j.dumps({"id":f"log_{int(datetime.now().timestamp()*1000)}","timestamp":int(datetime.now().timestamp()*1000),"location":loc,"message":msg,"data":data or {},"runId":"ia_mother_run","hypothesisId":hyp or ""})+"\n")
# #endregion

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("IA_MOTHER_BOT_TOKEN")
CORE_API_URL = os.getenv("CORE_API_URL")
REDIS_URL = os.getenv("REDIS_URL")
TON_API_KEY = os.getenv("TON_API_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")

# Telegram API credentials
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

_dbg("ia_mother.py:module", "Module loaded", {"api_id": TELEGRAM_API_ID, "api_hash_len": len(TELEGRAM_API_HASH), "bot_token": bool(TELEGRAM_BOT_TOKEN), "redis_url": REDIS_URL or ""}, "H1")

# Initialize services - only if REDIS_URL is set and non-empty
redis_client = None
if REDIS_URL:
    try:
        import redis as _redis_mod
        redis_client = _redis_mod.from_url(REDIS_URL)
        _dbg("ia_mother.py:redis", "Redis connected", hypothesis_id="H3")
    except Exception as _re:
        _dbg("ia_mother.py:redis", f"Redis connection failed: {_re}", {"error": str(_re)}, "H3")

health_app = None
try:
    from fastapi import FastAPI
    health_app = FastAPI(title="IA-Mother Bot")
except ImportError:
    pass

class IAMotherBot:
    """IA-Mother - Маркетплейс и обменник"""
    
    def __init__(self):
        self.client = TelegramClient('ia_mother', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        self.is_running = False
        
        # Exchange rates (обновляются динамически)
        self.exchange_rates = {
            "stars_to_ia_coin": Decimal("0.01"),  # 1 Star = 0.01 IA-Coin
            "ia_coin_to_stars": Decimal("100")    # 1 IA-Coin = 100 Stars
        }
        
        logger.info("IA-Mother Bot инициализирован")
    
    async def start(self):
        """Запуск бота"""
        try:
            _dbg("ia_mother.py:start", "Calling client.start()", {"api_id": TELEGRAM_API_ID, "token_prefix": TELEGRAM_BOT_TOKEN[:20] if TELEGRAM_BOT_TOKEN else "NONE"}, "H1")
            await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
            self.is_running = True
            _dbg("ia_mother.py:start", "client.start() succeeded", hypothesis_id="H1")
            
            me = await self.client.get_me()
            _dbg("ia_mother.py:start", "Bot identity", {"id": me.id, "username": me.username, "name": me.first_name}, "H1")
            
            self.register_handlers()
            _dbg("ia_mother.py:start", "Handlers registered", hypothesis_id="H2")
            
            logger.info(f"IA-Mother Bot запущен как @{me.username}")
            
        except Exception as e:
            _dbg("ia_mother.py:start", f"Start failed: {e}", {"error_type": type(e).__name__, "error": str(e)}, "H1")
            logger.error(f"Ошибка запуска IA-Mother: {e}")
            raise
    
    def register_handlers(self):
        """Регистрация обработчиков команд"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Главное меню IA-Mother"""
            _dbg("ia_mother.py:start_handler", "/start received", {"sender_id": event.sender_id}, "H2")
            user = await event.get_sender()
            
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
                [Button.inline("ℹ️ Помощь", b"help")]
            ]
            
            await event.respond(welcome_msg, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=b"marketplace"))
        async def marketplace_handler(event):
            """Маркетплейс ботов и навыков"""
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
                    [Button.inline("⬅️ Назад", b"back_main")]
                ]
            )
        
        @self.client.on(events.CallbackQuery(pattern=b"marketplace_bots"))
        async def marketplace_bots_handler(event):
            """Каталог ботов"""
            bots = await self.get_marketplace_bots()
            
            if not bots:
                await event.edit(
                    "🤖 **Каталог ботов**\n\n"
                    "Пока что ботов нет, но скоро они появятся!\n"
                    "Создайте своего первого бота прямо сейчас! 🚀",
                    buttons=[
                        [Button.inline("➕ Создать бота", b"create_bot")],
                        [Button.inline("⬅️ Назад", b"marketplace")]
                    ]
                )
                return
            
            bot_list = "🤖 **Доступные боты:**\n\n"
            buttons = []
            
            for bot in bots[:10]:  # Показываем первые 10
                bot_list += (
                    f"**{bot['name']}**\n"
                    f"👤 {bot['creator']}\n"
                    f"💰 {bot['price']} IA-Coins\n"
                    f"⭐ {bot['rating']}/5 ({bot['reviews']} отзывов)\n\n"
                )
                buttons.append([Button.inline(
                    f"🔍 {bot['name']}", 
                    f"view_bot_{bot['id']}".encode()
                )])
            
            buttons.extend([
                [Button.inline("📄 Больше ботов", b"marketplace_bots_more")],
                [Button.inline("⬅️ Назад", b"marketplace")]
            ])
            
            await event.edit(bot_list, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=b"marketplace_skills"))
        async def marketplace_skills_handler(event):
            """Каталог навыков"""
            skills = await self.get_marketplace_skills()
            
            skill_list = "🧠 **Доступные навыки:**\n\n"
            buttons = []
            
            for skill in skills[:10]:
                skill_list += (
                    f"**{skill['name']}** v{skill['version']}\n"
                    f"📝 {skill['description']}\n"
                    f"🏷️ {skill['category_name']} {skill.get('category_icon', '')}\n"
                    f"💰 {skill['price_ia_coins']} IA-Coins"
                    f"{' (Бесплатно)' if skill['is_free'] else ''}\n"
                    f"⭐ {skill['average_rating']}/5 ({skill['total_installations']} установок)\n"
                    f"👨‍💻 {skill['creator_name']}\n\n"
                )
                buttons.append([Button.inline(
                    f"🔍 {skill['name']}", 
                    f"view_skill_{skill['id']}".encode()
                )])
            
            buttons.extend([
                [Button.inline("🔍 Поиск навыков", b"search_skills")],
                [Button.inline("📂 По категориям", b"skills_categories")],
                [Button.inline("🔥 Популярные", b"skills_featured")],
                [Button.inline("➕ Создать навык", b"create_skill")],
                [Button.inline("⬅️ Назад", b"marketplace")]
            ])
            
            await event.edit(skill_list, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=b"skills_categories"))
        async def skills_categories_handler(event):
            """Категории навыков"""
            categories = await self.get_skill_categories()
            
            category_list = "📂 **Категории навыков:**\n\n"
            buttons = []
            
            for category in categories:
                category_list += (
                    f"{category['icon']} **{category['name']}**\n"
                    f"📊 {category['skills_count']} навыков\n\n"
                )
                buttons.append([Button.inline(
                    f"{category['icon']} {category['name']} ({category['skills_count']})",
                    f"category_skills_{category['id']}".encode()
                )])
            
            buttons.append([Button.inline("⬅️ Назад", b"marketplace_skills")])
            await event.edit(category_list, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=b"skills_featured"))
        async def skills_featured_handler(event):
            """Популярные навыки"""
            skills = await self.get_featured_skills()
            
            skill_list = "🔥 **Популярные навыки:**\n\n"
            buttons = []
            
            for i, skill in enumerate(skills[:10], 1):
                popularity_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}️⃣"
                skill_list += (
                    f"{popularity_emoji} **{skill['name']}**\n"
                    f"📊 Популярность: {skill['popularity_score']:.1f}/10\n"
                    f"💰 {skill['price_ia_coins']} IA-Coins\n"
                    f"⭐ {skill['average_rating']}/5 ({skill['total_installations']} установок)\n\n"
                )
                buttons.append([Button.inline(
                    f"{popularity_emoji} {skill['name']}", 
                    f"view_skill_{skill['id']}".encode()
                )])
            
            buttons.append([Button.inline("⬅️ Назад", b"marketplace_skills")])
            await event.edit(skill_list, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=b"create_skill"))
        async def create_skill_handler(event):
            """Создание нового навыка"""
            user = await event.get_sender()
            webapp_url = f"{WEBAPP_URL}/create-skill?user_id={user.id}"
            
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
                    [Button.inline("⬅️ Назад", b"marketplace_skills")]
                ]
            )
        
        @self.client.on(events.CallbackQuery(pattern=rb"view_skill_(.+)"))
        async def view_skill_handler(event):
            """Просмотр конкретного навыка"""
            skill_id = event.pattern_match.group(1).decode()
            skill = await self.get_skill_details(skill_id)
            
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
            
            if skill.get('requirements'):
                skill_info += f"⚠️ **Требования:** {', '.join(skill['requirements'])}\n"
            
            buttons = [
                [Button.inline("💾 Установить навык", f"install_skill_{skill_id}".encode())],
                [Button.inline("⭐ Оценить", f"rate_skill_{skill_id}".encode()),
                 Button.inline("💬 Отзывы", f"skill_reviews_{skill_id}".encode())],
                [Button.inline("📊 Статистика", f"skill_stats_{skill_id}".encode())],
                [Button.inline("⬅️ Назад", b"marketplace_skills")]
            ]
            
            await event.edit(skill_info, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=rb"install_skill_(.+)"))
        async def install_skill_handler(event):
            """Установка навыка на бота"""
            skill_id = event.pattern_match.group(1).decode()
            user = await event.get_sender()
            
            # Получение ботов пользователя
            user_bots = await self.get_user_bots(user.id)
            
            if not user_bots:
                await event.edit(
                    "🤖 **Установка навыка**\n\n"
                    "У вас нет ботов для установки навыка.\n"
                    "Сначала создайте бота!",
                    buttons=[
                        [Button.inline("➕ Создать бота", b"create_bot")],
                        [Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())]
                    ]
                )
                return
            
            bot_list = "🤖 **Выберите бота для установки навыка:**\n\n"
            buttons = []
            
            for bot in user_bots[:10]:
                status_emoji = "🟢" if bot['status'] == 'active' else "🔴"
                bot_list += f"{status_emoji} **{bot['name']}** (Уровень {bot['level']})\n"
                buttons.append([Button.inline(
                    f"{status_emoji} {bot['name']}",
                    f"confirm_install_{skill_id}_{bot['id']}".encode()
                )])
            
            buttons.append([Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())])
            await event.edit(bot_list, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=rb"confirm_install_(.+)_(.+)"))
        async def confirm_install_handler(event):
            """Подтверждение установки навыка"""
            match = event.pattern_match
            skill_id = match.group(1).decode()
            bot_id = match.group(2).decode()
            
            skill = await self.get_skill_details(skill_id)
            bot = await self.get_bot_details(bot_id)
            
            if not skill or not bot:
                await event.answer("Данные не найдены", alert=True)
                return
            
            confirm_text = (
                f"💾 **Подтверждение установки**\n\n"
                f"🧠 **Навык:** {skill['name']} v{skill['version']}\n"
                f"🤖 **Бот:** {bot['name']}\n"
                f"💰 **Цена:** {skill['price_ia_coins']} IA-Coins\n\n"
                f"После установки навык будет доступен в вашем боте.\n"
                f"Вы сможете настроить его параметры в панели управления.\n\n"
                f"Продолжить установку?"
            )
            
            buttons = [
                [Button.inline("✅ Установить", f"process_install_{skill_id}_{bot_id}".encode())],
                [Button.inline("⬅️ Отмена", f"install_skill_{skill_id}".encode())]
            ]
            
            await event.edit(confirm_text, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=rb"process_install_(.+)_(.+)"))
        async def process_install_handler(event):
            """Обработка установки навыка"""
            match = event.pattern_match
            skill_id = match.group(1).decode()
            bot_id = match.group(2).decode()
            user = await event.get_sender()
            
            try:
                # Отправка запроса на установку в Core API
                result = await self.install_skill_on_bot(
                    skill_id=skill_id,
                    bot_id=bot_id,
                    user_id=user.id
                )
                
                if result['success']:
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
                            [Button.inline("🏪 Продолжить покупки", b"marketplace_skills")]
                        ]
                    )
                else:
                    await event.edit(
                        f"❌ **Ошибка установки**\n\n"
                        f"Причина: {result['error']}\n\n"
                        f"Попробуйте еще раз или обратитесь в поддержку.",
                        buttons=[
                            [Button.inline("🔄 Повторить", f"process_install_{skill_id}_{bot_id}".encode())],
                            [Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())]
                        ]
                    )
                    
            except Exception as e:
                logger.error(f"Ошибка установки навыка: {e}")
                await event.edit(
                    f"❌ **Техническая ошибка**\n\n"
                    f"Не удалось установить навык.\n"
                    f"Попробуйте позже или обратитесь в поддержку.",
                    buttons=[
                        [Button.inline("⬅️ Назад", f"view_skill_{skill_id}".encode())]
                    ]
                )
        
        @self.client.on(events.CallbackQuery(pattern=b"exchange"))
        async def exchange_handler(event):
            """Обменник валют"""
            user = await event.get_sender()
            balance = await self.get_user_balance(user.id)
            
            await event.edit(
                f"💱 **Обменник IA-Mother**\n\n"
                f"**Ваш баланс:**\n"
                f"⭐ {balance['stars']} Stars\n"
                f"🪙 {balance['ia_coins']} IA-Coins\n\n"
                f"**Текущие курсы:**\n"
                f"1 Star = {self.exchange_rates['stars_to_ia_coin']} IA-Coin\n"
                f"1 IA-Coin = {self.exchange_rates['ia_coin_to_stars']} Stars\n\n"
                f"Что хотите обменять?",
                buttons=[
                    [Button.inline("⭐→🪙 Stars → IA-Coins", b"exchange_stars_to_ia")],
                    [Button.inline("🪙→⭐ IA-Coins → Stars", b"exchange_ia_to_stars")],
                    [Button.inline("📈 История операций", b"exchange_history")],
                    [Button.inline("⬅️ Назад", b"back_main")]
                ]
            )
        
        @self.client.on(events.CallbackQuery(pattern=b"exchange_stars_to_ia"))
        async def exchange_stars_to_ia_handler(event):
            """Обмен Stars на IA-Coins"""
            await event.edit(
                "⭐→🪙 **Обмен Stars на IA-Coins**\n\n"
                "Введите количество Stars для обмена:\n"
                "(Минимум: 100 Stars)",
                buttons=[
                    [Button.inline("100 ⭐", b"exchange_100_stars")],
                    [Button.inline("500 ⭐", b"exchange_500_stars")],
                    [Button.inline("1000 ⭐", b"exchange_1000_stars")],
                    [Button.inline("✏️ Другая сумма", b"exchange_custom_stars")],
                    [Button.inline("⬅️ Назад", b"exchange")]
                ]
            )
        
        @self.client.on(events.CallbackQuery(pattern=b"my_bots"))
        async def my_bots_handler(event):
            """Мои боты"""
            user = await event.get_sender()
            bots = await self.get_user_bots(user.id)
            
            if not bots:
                await event.edit(
                    "🤖 **Мои боты**\n\n"
                    "У вас пока нет ботов.\n"
                    "Создайте своего первого бота! 🚀",
                    buttons=[
                        [Button.inline("➕ Создать бота", b"create_bot")],
                        [Button.inline("🏪 Купить бота", b"marketplace_bots")],
                        [Button.inline("⬅️ Назад", b"back_main")]
                    ]
                )
                return
            
            bot_list = "🤖 **Ваши боты:**\n\n"
            buttons = []
            
            for bot in bots:
                status_emoji = "🟢" if bot['status'] == 'active' else "🔴"
                bot_list += (
                    f"{status_emoji} **{bot['name']}**\n"
                    f"📊 Уровень: {bot['level']}\n"
                    f"💬 Сообщений: {bot['message_count']}\n"
                    f"💰 Доход: {bot['revenue']} IA-Coins\n\n"
                )
                buttons.append([Button.inline(
                    f"⚙️ {bot['name']}", 
                    f"manage_bot_{bot['id']}".encode()
                )])
            
            buttons.extend([
                [Button.inline("➕ Создать нового", b"create_bot")],
                [Button.inline("⬅️ Назад", b"back_main")]
            ])
            
            await event.edit(bot_list, buttons=buttons)
        
        @self.client.on(events.CallbackQuery(pattern=b"create_bot"))
        async def create_bot_handler(event):
            """Создание нового бота"""
            webapp_url = f"{WEBAPP_URL}/create-bot"
            
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
                    [Button.inline("⬅️ Назад", b"my_bots")]
                ]
            )
        
        @self.client.on(events.CallbackQuery(pattern=b"stats"))
        async def stats_handler(event):
            """Статистика платформы"""
            stats = await self.get_platform_stats()
            
            await event.edit(
                f"📊 **Статистика Zero Bot**\n\n"
                f"🤖 **Боты:** {stats['total_bots']}\n"
                f"👥 **Пользователи:** {stats['total_users']}\n"
                f"🧠 **Навыки:** {stats['total_skills']}\n"
                f"👑 **Личности:** {stats['total_personalities']}\n\n"
                f"💰 **Экономика:**\n"
                f"🪙 IA-Coins в обороте: {stats['ia_coins_supply']}\n"
                f"💎 NFT Паспортов: {stats['nft_passports']}\n"
                f"💸 Объем торгов: {stats['trading_volume']} IA-Coins\n\n"
                f"🔥 **За последние 24 часа:**\n"
                f"📈 Новых ботов: {stats['new_bots_24h']}\n"
                f"💬 Сообщений: {stats['messages_24h']}\n"
                f"💰 Транзакций: {stats['transactions_24h']}",
                buttons=[
                    [Button.inline("📈 Подробная аналитика", b"detailed_stats")],
                    [Button.inline("⬅️ Назад", b"back_main")]
                ]
            )
        
        @self.client.on(events.CallbackQuery(pattern=b"back_main"))
        async def back_main_handler(event):
            """Возврат в главное меню"""
            await start_handler(event)
    
    async def get_marketplace_bots(self) -> List[Dict]:
        """Получение списка ботов из маркетплейса"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/marketplace/bots/")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения ботов: {e}")
        
        # Заглушка для демонстрации
        return [
            {
                "id": "1",
                "name": "Помощник Программиста",
                "creator": "@developer123",
                "price": "50",
                "rating": "4.8",
                "reviews": "127"
            },
            {
                "id": "2", 
                "name": "Учитель Английского",
                "creator": "@teacher_ai",
                "price": "30",
                "rating": "4.9",
                "reviews": "89"
            }
        ]
    
    async def get_marketplace_skills(self) -> List[Dict]:
        """Получение списка навыков из маркетплейса"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/skills/skills/")
                if response.status_code == 200:
                    return response.json().get('results', [])
        except Exception as e:
            logger.error(f"Ошибка получения навыков: {e}")
        
        # Заглушка для демонстрации
        return [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Генерация кода Python",
                "description": "Автоматическая генерация кода на Python с использованием AI",
                "version": "1.2.0",
                "creator_name": "@ai_developer",
                "category_name": "Разработка",
                "category_icon": "💻",
                "price_ia_coins": "25.00",
                "is_free": False,
                "average_rating": "4.7",
                "total_installations": 156,
                "popularity_score": 8.5,
                "execution_type": "api_call",
                "tags": ["python", "code", "ai", "development"],
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "Умный переводчик",
                "description": "Перевод текста между 50+ языками с контекстным пониманием",
                "version": "2.0.1",
                "creator_name": "@linguist_pro",
                "category_name": "Языки",
                "category_icon": "🌍",
                "price_ia_coins": "15.00",
                "is_free": False,
                "average_rating": "4.9",
                "total_installations": 342,
                "popularity_score": 9.2,
                "execution_type": "api_call",
                "tags": ["translation", "languages", "nlp"],
                "created_at": "2024-01-10T14:20:00Z"
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "name": "Анализ настроения",
                "description": "Определение эмоционального окраса текста и настроения пользователя",
                "version": "1.0.0",
                "creator_name": "@emotion_ai",
                "category_name": "Анализ",
                "category_icon": "😊",
                "price_ia_coins": "0.00",
                "is_free": True,
                "average_rating": "4.3",
                "total_installations": 89,
                "popularity_score": 6.8,
                "execution_type": "langflow_node",
                "tags": ["sentiment", "emotion", "analysis", "free"],
                "created_at": "2024-02-01T09:15:00Z"
            }
        ]
    
    async def get_skill_categories(self) -> List[Dict]:
        """Получение категорий навыков"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/skills/categories/")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения категорий: {e}")
        
        # Заглушка
        return [
            {"id": 1, "name": "Разработка", "icon": "💻", "skills_count": 45},
            {"id": 2, "name": "Языки", "icon": "🌍", "skills_count": 23},
            {"id": 3, "name": "Анализ", "icon": "📊", "skills_count": 18},
            {"id": 4, "name": "Творчество", "icon": "🎨", "skills_count": 12},
            {"id": 5, "name": "Утилиты", "icon": "🛠️", "skills_count": 31}
        ]
    
    async def get_featured_skills(self) -> List[Dict]:
        """Получение популярных навыков"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/skills/skills/featured/")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения популярных навыков: {e}")
        
        # Заглушка - возвращаем отсортированные по популярности
        skills = await self.get_marketplace_skills()
        return sorted(skills, key=lambda x: x['popularity_score'], reverse=True)
    
    async def get_skill_details(self, skill_id: str) -> Optional[Dict]:
        """Получение детальной информации о навыке"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/skills/skills/{skill_id}/")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения навыка {skill_id}: {e}")
        
        # Заглушка - ищем в mock данных
        skills = await self.get_marketplace_skills()
        for skill in skills:
            if skill['id'] == skill_id:
                # Добавляем дополнительные поля для детального просмотра
                skill.update({
                    'ratings_count': 23,
                    'requirements': ['Python 3.8+', 'API ключ'],
                    'capabilities': ['text_processing', 'code_generation'],
                    'config_schema': {
                        'api_key': {'type': 'string', 'required': True},
                        'temperature': {'type': 'float', 'default': 0.7}
                    }
                })
                return skill
        return None
    
    async def get_bot_details(self, bot_id: str) -> Optional[Dict]:
        """Получение информации о боте"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/bot-core/bot-passports/{bot_id}/")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения бота {bot_id}: {e}")
        
        # Заглушка
        return {
            "id": bot_id,
            "name": f"Бот {bot_id[:8]}",
            "level": 5,
            "status": "active"
        }
    
    async def install_skill_on_bot(self, skill_id: str, bot_id: str, user_id: int) -> Dict:
        """Установка навыка на бота"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CORE_API_URL}/api/v1/skills/skills/{skill_id}/install/",
                    json={
                        "bot_passport_id": bot_id,
                        "config": {}
                    },
                    headers={"Authorization": f"Bearer {await self.get_user_token(user_id)}"}
                )
                
                if response.status_code == 201:
                    result = response.json()
                    return {
                        "success": True,
                        "installation_id": result.get('id'),
                        "skill_name": result.get('skill', {}).get('name', 'Unknown'),
                        "bot_name": result.get('bot_passport_name', 'Unknown'),
                        "price_paid": result.get('price_paid', '0.00')
                    }
                else:
                    error_data = response.json()
                    return {
                        "success": False,
                        "error": error_data.get('error', 'Неизвестная ошибка')
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка установки навыка: {e}")
            return {
                "success": False,
                "error": f"Техническая ошибка: {str(e)}"
            }
    
    async def get_user_token(self, user_id: int) -> str:
        """Получение токена пользователя для API запросов"""
        # TODO: Реализовать получение JWT токена пользователя
        # Пока возвращаем заглушку
        return f"mock_token_for_user_{user_id}"
    
    async def get_user_balance(self, user_id: int) -> Dict:
        """Получение баланса пользователя"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CORE_API_URL}/api/v1/users/{user_id}/balance/"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
        
        # Заглушка
        return {
            "stars": "1000",
            "ia_coins": "10.50"
        }
    
    async def get_user_bots(self, user_id: int) -> List[Dict]:
        """Получение ботов пользователя"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CORE_API_URL}/api/v1/users/{user_id}/bots/"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения ботов пользователя: {e}")
        
        # Заглушка
        return [
            {
                "id": "bot_1",
                "name": "Мой Помощник",
                "status": "active",
                "level": "5",
                "message_count": "1,247",
                "revenue": "125.50"
            }
        ]
    
    async def get_platform_stats(self) -> Dict:
        """Получение статистики платформы"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CORE_API_URL}/api/v1/stats/")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
        
        # Заглушка
        return {
            "total_bots": "1,247",
            "total_users": "5,892",
            "total_skills": "156",
            "total_personalities": "89",
            "ia_coins_supply": "1,250,000",
            "nft_passports": "1,247",
            "trading_volume": "45,892",
            "new_bots_24h": "23",
            "messages_24h": "15,678",
            "transactions_24h": "234"
        }
    
    async def process_exchange(self, user_id: int, from_currency: str, 
                            to_currency: str, amount: Decimal) -> Dict:
        """Обработка обмена валют"""
        try:
            # Проверка баланса
            balance = await self.get_user_balance(user_id)
            
            if from_currency == "stars":
                if Decimal(balance["stars"]) < amount:
                    return {"success": False, "error": "Недостаточно Stars"}
                
                ia_coins_amount = amount * self.exchange_rates["stars_to_ia_coin"]
                
                # Обновление баланса через API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{CORE_API_URL}/api/v1/exchange/",
                        json={
                            "user_id": user_id,
                            "from_currency": "stars",
                            "to_currency": "ia_coins",
                            "from_amount": str(amount),
                            "to_amount": str(ia_coins_amount),
                            "rate": str(self.exchange_rates["stars_to_ia_coin"])
                        }
                    )
                    
                    if response.status_code == 200:
                        return {
                            "success": True,
                            "from_amount": amount,
                            "to_amount": ia_coins_amount,
                            "rate": self.exchange_rates["stars_to_ia_coin"]
                        }
            
            return {"success": False, "error": "Ошибка обработки"}
            
        except Exception as e:
            logger.error(f"Ошибка обмена: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_exchange_rates(self):
        """Обновление курсов валют"""
        while self.is_running:
            try:
                # Получение актуальных курсов из Core API
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{CORE_API_URL}/api/v1/exchange/rates/")
                    if response.status_code == 200:
                        rates = response.json()
                        self.exchange_rates.update(rates)
                        logger.info("Курсы валют обновлены")
                
            except Exception as e:
                logger.error(f"Ошибка обновления курсов: {e}")
            
            await asyncio.sleep(300)  # Обновление каждые 5 минут
    
    async def stop(self):
        """Остановка бота"""
        self.is_running = False
        await self.client.disconnect()
        logger.info("IA-Mother Bot остановлен")

# Health check endpoint
@health_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ia-mother",
        "timestamp": datetime.utcnow().isoformat()
    }

@health_app.get("/stats")
async def get_health_stats():
    return {
        "service": "ia-mother",
        "uptime": "calculated_uptime",
        "active_users": "stored_count",
        "exchange_volume": "daily_volume"
    }

# Main execution
async def main():
    """Основная функция"""
    bot = IAMotherBot()
    
    try:
        # Запуск бота
        await bot.start()
        
        # Запуск health check сервера
        config = uvicorn.Config(health_app, host="0.0.0.0", port=8002, log_level="info")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        
        # Основной цикл
        await bot.client.run_until_disconnected()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка IA-Mother: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())