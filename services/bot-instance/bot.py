"""
Individual Bot Instance - Каждый бот в отдельном контейнере
Интегрируется с Langflow для управления промптами
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
import redis
from telethon import TelegramClient, events
from telethon.tl.types import User
from fastapi import FastAPI
from loguru import logger
import uvicorn

# Configuration from environment
BOT_CONFIG = json.loads(os.getenv("BOT_CONFIG", "{}"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CORE_API_URL = os.getenv("CORE_API_URL")
REDIS_URL = os.getenv("REDIS_URL")
BOT_CHANNEL = os.getenv("BOT_CHANNEL")
BOT_PASSPORT_ID = os.getenv("BOT_PASSPORT_ID")

# Initialize services
redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None
health_app = FastAPI(title=f"Bot Instance {BOT_PASSPORT_ID}")

class ZeroBotInstance:
    """Индивидуальный экземпляр Zero Bot"""
    
    def __init__(self):
        self.config = BOT_CONFIG
        self.bot_data = self.config.get("bot_data", {})
        self.personality_data = self.config.get("personality_data", {})
        self.langflow_config = self.config.get("langflow_config", {})
        
        # Telegram client
        api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        api_hash = os.getenv("TELEGRAM_API_HASH", "")
        
        if not api_id or not api_hash:
            raise ValueError("TELEGRAM_API_ID и TELEGRAM_API_HASH обязательны")
        
        self.client = TelegramClient(
            f'bot_{BOT_PASSPORT_ID}',
            api_id,
            api_hash
        )
        
        # State
        self.is_running = False
        self.conversation_contexts = {}
        
        logger.info(f"Инициализирован бот {BOT_PASSPORT_ID}")
    
    async def start(self):
        """Запуск бота"""
        try:
            await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
            self.is_running = True
            
            # Регистрация обработчиков
            self.register_handlers()
            
            # Подписка на обновления конфигурации
            if redis_client:
                asyncio.create_task(self.listen_for_config_updates())
            
            # Отправка heartbeat
            asyncio.create_task(self.heartbeat_loop())
            
            logger.info(f"Бот {BOT_PASSPORT_ID} запущен")
            
            # Уведомление Core API о запуске
            await self.notify_core_api("bot_started")
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
    
    def register_handlers(self):
        """Регистрация обработчиков сообщений"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Обработчик команды /start"""
            user = await event.get_sender()
            
            # Проверка владельца
            if await self.is_owner(user):
                welcome_msg = self.get_welcome_message()
            else:
                welcome_msg = self.get_guest_message()
            
            await event.respond(welcome_msg)
            
            # Логирование
            await self.log_interaction(user, "/start", welcome_msg)
        
        @self.client.on(events.NewMessage(pattern='/config'))
        async def config_handler(event):
            """Обработчик команды /config - открытие Langflow WebApp"""
            user = await event.get_sender()
            
            if not await self.is_owner(user):
                await event.respond("❌ Только владелец может настраивать бота")
                return
            
            webapp_url = self.get_langflow_webapp_url()
            
            await event.respond(
                "🎛️ **Настройка бота**\n\n"
                "Нажмите кнопку ниже для открытия панели управления:",
                buttons=[
                    [self.client.build_reply_markup([
                        {"text": "🚀 Открыть Langflow", "url": webapp_url}
                    ])]
                ]
            )
        
        @self.client.on(events.NewMessage(func=lambda e: not e.text.startswith('/')))
        async def message_handler(event):
            """Основной обработчик сообщений"""
            user = await event.get_sender()
            message_text = event.text
            
            try:
                # Получение контекста разговора
                context = self.get_conversation_context(user.id)
                
                # Обработка через Langflow или базовую логику
                if self.langflow_config.get("enabled"):
                    response = await self.process_with_langflow(message_text, context, user)
                else:
                    response = await self.process_with_personality(message_text, context, user)
                
                # Отправка ответа
                await event.respond(response)
                
                # Обновление контекста
                self.update_conversation_context(user.id, message_text, response)
                
                # Логирование
                await self.log_interaction(user, message_text, response)
                
                # Начисление XP владельцу
                if await self.is_owner(user):
                    await self.add_experience_points(1)
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
                await event.respond("😅 Извините, произошла ошибка. Попробуйте еще раз.")
    
    async def process_with_langflow(self, message: str, context: Dict, user: User) -> str:
        """Обработка сообщения через Langflow"""
        try:
            langflow_url = self.langflow_config.get("api_url")
            flow_id = self.langflow_config.get("flow_id")
            
            if not langflow_url or not flow_id:
                return await self.process_with_personality(message, context, user)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{langflow_url}/api/v1/run/{flow_id}",
                    json={
                        "input_value": message,
                        "context": context,
                        "user_info": {
                            "id": user.id,
                            "username": user.username,
                            "first_name": user.first_name
                        },
                        "bot_info": {
                            "passport_id": BOT_PASSPORT_ID,
                            "personality": self.personality_data
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("output", "Не удалось получить ответ")
                else:
                    logger.error(f"Ошибка Langflow: {response.status_code}")
                    return await self.process_with_personality(message, context, user)
                    
        except Exception as e:
            logger.error(f"Ошибка Langflow: {e}")
            return await self.process_with_personality(message, context, user)
    
    async def process_with_personality(self, message: str, context: Dict, user: User) -> str:
        """Базовая обработка через личность"""
        try:
            if not self.personality_data:
                return "👋 Привет! Я Zero Bot. Моя личность еще не настроена."
            
            system_prompt = self.personality_data.get("system_prompt", "")
            
            # Простая обработка (в реальной системе здесь был бы вызов LLM)
            if "привет" in message.lower():
                return f"👋 Привет! Я {self.bot_data.get('name', 'Zero Bot')}. Как дела?"
            elif "как дела" in message.lower():
                return "Отлично! Готов помочь вам 😊"
            elif "помощь" in message.lower():
                return self.get_help_message()
            else:
                return f"Интересно! Вы сказали: '{message}'. Расскажите больше!"
                
        except Exception as e:
            logger.error(f"Ошибка обработки личности: {e}")
            return "😅 Извините, не могу обработать ваше сообщение прямо сейчас."
    
    async def is_owner(self, user: User) -> bool:
        """Проверка, является ли пользователь владельцем бота"""
        # В реальной системе здесь была бы проверка через TON адрес
        owner_ton_address = self.config.get("owner_ton_address")
        
        # Временная заглушка - проверка через Core API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{CORE_API_URL}/api/v1/bot-core/bot-passports/{BOT_PASSPORT_ID}/owner-check/",
                    params={"telegram_user_id": user.id}
                )
                return response.status_code == 200 and response.json().get("is_owner", False)
        except:
            return False
    
    def get_conversation_context(self, user_id: int) -> Dict:
        """Получение контекста разговора"""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = {
                "messages": [],
                "created_at": datetime.utcnow().isoformat()
            }
        return self.conversation_contexts[user_id]
    
    def update_conversation_context(self, user_id: int, user_message: str, bot_response: str):
        """Обновление контекста разговора"""
        context = self.get_conversation_context(user_id)
        context["messages"].append({
            "user": user_message,
            "bot": bot_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Ограничение размера контекста
        if len(context["messages"]) > 50:
            context["messages"] = context["messages"][-50:]
    
    def get_welcome_message(self) -> str:
        """Приветственное сообщение для владельца"""
        bot_name = self.bot_data.get("name", "Zero Bot")
        return (
            f"🤖 **{bot_name}**\n\n"
            f"Привет, хозяин! Я ваш персональный Zero Bot.\n\n"
            f"**Доступные команды:**\n"
            f"• /config - Настройка через Langflow\n"
            f"• /stats - Статистика бота\n"
            f"• /help - Помощь\n\n"
            f"Просто напишите мне что-нибудь, и я отвечу! 💬"
        )
    
    def get_guest_message(self) -> str:
        """Сообщение для гостей"""
        bot_name = self.bot_data.get("name", "Zero Bot")
        return (
            f"👋 Привет! Я {bot_name}.\n\n"
            f"Я персональный бот, но могу немного поболтать с вами!\n"
            f"Напишите что-нибудь интересное 😊"
        )
    
    def get_help_message(self) -> str:
        """Сообщение помощи"""
        return (
            "🆘 **Помощь**\n\n"
            "Я умею:\n"
            "• Отвечать на ваши сообщения\n"
            "• Запоминать контекст разговора\n"
            "• Использовать настроенную личность\n"
            "• Работать через Langflow (если настроено)\n\n"
            "Просто пишите мне, и я буду отвечать! 💬"
        )
    
    def get_langflow_webapp_url(self) -> str:
        """URL для Langflow WebApp"""
        webapp_base = os.getenv("WEBAPP_URL", "https://your-domain.com")
        return f"{webapp_base}/langflow?bot_id={BOT_PASSPORT_ID}"
    
    async def log_interaction(self, user: User, message: str, response: str):
        """Логирование взаимодействия"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/bot-interactions/",
                    json={
                        "bot_passport_id": BOT_PASSPORT_ID,
                        "user_telegram_id": user.id,
                        "user_message": message,
                        "bot_response": response,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка логирования: {e}")
    
    async def add_experience_points(self, points: int):
        """Начисление XP боту"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/bot-core/bot-passports/{BOT_PASSPORT_ID}/add_experience/",
                    json={"points": points}
                )
        except Exception as e:
            logger.error(f"Ошибка начисления XP: {e}")
    
    async def notify_core_api(self, event_type: str):
        """Уведомление Core API о событиях"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/bot-events/",
                    json={
                        "event_type": event_type,
                        "bot_id": BOT_PASSPORT_ID,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка уведомления Core API: {e}")
    
    async def listen_for_config_updates(self):
        """Прослушивание обновлений конфигурации"""
        if not redis_client:
            return
        
        pubsub = redis_client.pubsub()
        pubsub.subscribe(BOT_CHANNEL)
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        if data.get('type') == 'config_update':
                            await self.update_config(data.get('config', {}))
                    except Exception as e:
                        logger.error(f"Ошибка обработки обновления конфигурации: {e}")
        except Exception as e:
            logger.error(f"Ошибка прослушивания Redis: {e}")
    
    async def update_config(self, new_config: Dict):
        """Обновление конфигурации бота"""
        try:
            self.langflow_config.update(new_config.get("langflow_config", {}))
            logger.info("Конфигурация обновлена")
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
    
    async def heartbeat_loop(self):
        """Отправка heartbeat сигналов"""
        while self.is_running:
            try:
                if redis_client:
                    redis_client.setex(f"heartbeat:{BOT_PASSPORT_ID}", 60, "alive")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Ошибка heartbeat: {e}")
                await asyncio.sleep(30)
    
    async def stop(self):
        """Остановка бота"""
        self.is_running = False
        await self.client.disconnect()
        await self.notify_core_api("bot_stopped")
        logger.info(f"Бот {BOT_PASSPORT_ID} остановлен")

# Health check endpoint
@health_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "bot_id": BOT_PASSPORT_ID,
        "timestamp": datetime.utcnow().isoformat()
    }

@health_app.get("/stats")
async def get_stats():
    return {
        "bot_id": BOT_PASSPORT_ID,
        "config": BOT_CONFIG,
        "uptime": "calculated_uptime_here",
        "message_count": "stored_in_redis_or_db"
    }

# Main execution
async def main():
    """Основная функция"""
    bot = ZeroBotInstance()
    
    try:
        # Запуск бота
        await bot.start()
        
        # Запуск health check сервера в фоне
        config = uvicorn.Config(health_app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        
        # Основной цикл бота
        await bot.client.run_until_disconnected()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())