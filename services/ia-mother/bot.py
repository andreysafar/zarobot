"""
IA-Mother Bot: Telegram client, exchange rates, handler registration.
"""

import asyncio
from decimal import Decimal

from telethon import TelegramClient, events
from loguru import logger

import config
from core_api import CoreAPI
from handlers import exchange, marketplace, my_bots, start, stats


class IAMotherBot:
    """IA-Mother: Маркетплейс и обменник."""

    def __init__(self):
        self.client = TelegramClient(
            "ia_mother",
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH,
        )
        self.api = CoreAPI()
        self.is_running = False
        self.exchange_rates = {
            "stars_to_ia_coin": Decimal("0.01"),
            "ia_coin_to_stars": Decimal("100"),
        }
        logger.info("IA-Mother Bot инициализирован")

    async def start(self):
        try:
            config._dbg(
                "bot:start",
                "Calling client.start()",
                {"api_id": config.TELEGRAM_API_ID, "token_prefix": (config.TELEGRAM_BOT_TOKEN or "")[:20]},
                "H1",
            )
            await self.client.start(bot_token=config.TELEGRAM_BOT_TOKEN)
            self.is_running = True
            me = await self.client.get_me()
            config._dbg("bot:start", "Bot identity", {"id": me.id, "username": me.username}, "H1")
            self._register_handlers()
            config._dbg("bot:start", "Handlers registered", hyp="H2")
            logger.info(f"IA-Mother Bot запущен как @{me.username}")
        except Exception as e:
            config._dbg("bot:start", f"Start failed: {e}", {"error": str(e)}, "H1")
            logger.error(f"Ошибка запуска IA-Mother: {e}")
            raise

    def _register_handlers(self):
        client = self.client
        bot = self

        @client.on(events.NewMessage(pattern="/start"))
        async def on_start(event):
            await start.handle_start(event, bot)

        @client.on(events.CallbackQuery(pattern=b"back_main"))
        async def on_back_main(event):
            await start.handle_back_main(event, bot)

        @client.on(events.CallbackQuery(pattern=b"marketplace"))
        async def on_marketplace(event):
            await marketplace.handle_marketplace(event, bot)

        @client.on(events.CallbackQuery(pattern=b"marketplace_bots"))
        async def on_marketplace_bots(event):
            await marketplace.handle_marketplace_bots(event, bot)

        @client.on(events.CallbackQuery(pattern=b"marketplace_skills"))
        async def on_marketplace_skills(event):
            await marketplace.handle_marketplace_skills(event, bot)

        @client.on(events.CallbackQuery(pattern=b"skills_categories"))
        async def on_skills_categories(event):
            await marketplace.handle_skills_categories(event, bot)

        @client.on(events.CallbackQuery(pattern=b"skills_featured"))
        async def on_skills_featured(event):
            await marketplace.handle_skills_featured(event, bot)

        @client.on(events.CallbackQuery(pattern=b"create_skill"))
        async def on_create_skill(event):
            await marketplace.handle_create_skill(event, bot)

        @client.on(events.CallbackQuery(pattern=rb"view_skill_(.+)"))
        async def on_view_skill(event):
            await marketplace.handle_view_skill(event, bot)

        @client.on(events.CallbackQuery(pattern=rb"install_skill_(.+)"))
        async def on_install_skill(event):
            await marketplace.handle_install_skill(event, bot)

        @client.on(events.CallbackQuery(pattern=rb"confirm_install_(.+)_(.+)"))
        async def on_confirm_install(event):
            await marketplace.handle_confirm_install(event, bot)

        @client.on(events.CallbackQuery(pattern=rb"process_install_(.+)_(.+)"))
        async def on_process_install(event):
            await marketplace.handle_process_install(event, bot)

        @client.on(events.CallbackQuery(pattern=b"exchange"))
        async def on_exchange(event):
            await exchange.handle_exchange(event, bot)

        @client.on(events.CallbackQuery(pattern=b"exchange_stars_to_ia"))
        async def on_exchange_stars_to_ia(event):
            await exchange.handle_exchange_stars_to_ia(event, bot)

        @client.on(events.CallbackQuery(pattern=b"my_bots"))
        async def on_my_bots(event):
            await my_bots.handle_my_bots(event, bot)

        @client.on(events.CallbackQuery(pattern=b"create_bot"))
        async def on_create_bot(event):
            await my_bots.handle_create_bot(event, bot)

        @client.on(events.CallbackQuery(pattern=b"stats"))
        async def on_stats(event):
            await stats.handle_stats(event, bot)

    async def update_exchange_rates(self):
        """Background: refresh rates every 5 min."""
        while self.is_running:
            try:
                rates = await self.api.get_exchange_rates()
                if rates:
                    self.exchange_rates.update(rates)
                    logger.info("Курсы валют обновлены")
            except Exception as e:
                logger.error(f"Ошибка обновления курсов: {e}")
            await asyncio.sleep(300)

    async def stop(self):
        self.is_running = False
        await self.client.disconnect()
        logger.info("IA-Mother Bot остановлен")
