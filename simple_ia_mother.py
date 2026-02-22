#!/usr/bin/env python3
"""
Простая версия IA-Mother бота для демонстрации
Использует Telegram Bot API напрямую без Telethon
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
import httpx
from fastapi import FastAPI, Request
from loguru import logger
import uvicorn

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('IA_MOTHER_BOT_TOKEN')
CORE_API_URL = os.getenv('CORE_API_URL', 'http://localhost:8000')

# FastAPI app для webhook
app = FastAPI(title="IA-Mother Bot")

class SimpleIAMotherBot:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.core_api_url = CORE_API_URL
        
        logger.info(f"IA-Mother Bot инициализирован")
        logger.info(f"Core API: {self.core_api_url}")
    
    async def send_message(self, chat_id: int, text: str, reply_markup=None):
        """Отправка сообщения через Telegram Bot API"""
        async with httpx.AsyncClient() as client:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            
            response = await client.post(f"{self.api_url}/sendMessage", json=data)
            return response.json()
    
    async def get_marketplace_skills(self) -> List[Dict]:
        """Получить навыки из маркетплейса"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.core_api_url}/api/v1/skills/skills/")
                if response.status_code == 200:
                    data = response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"Ошибка получения навыков: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Ошибка подключения к Core API: {e}")
            return []
    
    async def get_skill_categories(self) -> List[Dict]:
        """Получить категории навыков"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.core_api_url}/api/v1/skills/categories/")
                if response.status_code == 200:
                    data = response.json()
                    return data.get('results', [])
                else:
                    logger.error(f"Ошибка получения категорий: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Ошибка подключения к Core API: {e}")
            return []
    
    async def handle_start(self, chat_id: int, user_name: str):
        """Обработка команды /start"""
        welcome_text = f"""
🤖 **Добро пожаловать в IA-Mother!**

Привет, {user_name}! Я ваш помощник в мире ботов и навыков.

🧠 **Доступные функции:**
• Маркетплейс навыков для ботов
• Каталог готовых ботов
• Обменник Stars ↔ IA-Coins
• Создание собственных навыков

Выберите действие:
        """
        
        keyboard = {
            'inline_keyboard': [
                [{'text': '🧠 Навыки', 'callback_data': 'marketplace_skills'}],
                [{'text': '🤖 Боты', 'callback_data': 'marketplace_bots'}],
                [{'text': '💰 Обменник', 'callback_data': 'exchange'}],
                [{'text': '📊 Статистика', 'callback_data': 'stats'}]
            ]
        }
        
        await self.send_message(chat_id, welcome_text, keyboard)
    
    async def handle_marketplace_skills(self, chat_id: int):
        """Обработка просмотра навыков"""
        skills = await self.get_marketplace_skills()
        
        if not skills:
            await self.send_message(chat_id, "❌ Навыки не найдены или ошибка подключения к API")
            return
        
        skills_text = "🧠 **Доступные навыки:**\n\n"
        keyboard_buttons = []
        
        for skill in skills[:5]:  # Показываем первые 5 навыков
            skills_text += (
                f"**{skill['name']}** v{skill['version']}\n"
                f"📝 {skill['description'][:100]}...\n"
                f"🏷️ {skill['category_name']} {skill.get('category_icon', '')}\n"
                f"💰 {skill['price_ia_coins']} IA-Coins"
                f"{' (Бесплатно)' if skill['is_free'] else ''}\n"
                f"⭐ {skill['average_rating']}/5 ({skill['total_installations']} установок)\n"
                f"👨‍💻 {skill['creator_name']}\n\n"
            )
            
            keyboard_buttons.append([{
                'text': f"🔍 {skill['name']}", 
                'callback_data': f"view_skill_{skill['id']}"
            }])
        
        keyboard_buttons.extend([
            [{'text': '📂 По категориям', 'callback_data': 'skills_categories'}],
            [{'text': '⬅️ Назад', 'callback_data': 'start'}]
        ])
        
        keyboard = {'inline_keyboard': keyboard_buttons}
        await self.send_message(chat_id, skills_text, keyboard)
    
    async def handle_skills_categories(self, chat_id: int):
        """Обработка просмотра категорий"""
        categories = await self.get_skill_categories()
        
        if not categories:
            await self.send_message(chat_id, "❌ Категории не найдены или ошибка подключения к API")
            return
        
        categories_text = "📂 **Категории навыков:**\n\n"
        keyboard_buttons = []
        
        for category in categories:
            categories_text += (
                f"{category['icon']} **{category['name']}**\n"
                f"📝 {category['description']}\n"
                f"📊 {category['skills_count']} навыков\n\n"
            )
            
            keyboard_buttons.append([{
                'text': f"{category['icon']} {category['name']} ({category['skills_count']})", 
                'callback_data': f"category_{category['id']}"
            }])
        
        keyboard_buttons.append([{'text': '⬅️ Назад', 'callback_data': 'marketplace_skills'}])
        
        keyboard = {'inline_keyboard': keyboard_buttons}
        await self.send_message(chat_id, categories_text, keyboard)

# Глобальный экземпляр бота
bot = SimpleIAMotherBot()

@app.post("/webhook")
async def webhook(request: Request):
    """Обработка webhook от Telegram"""
    try:
        data = await request.json()
        logger.info(f"Получен webhook: {data}")
        
        # Обработка сообщений
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            user_name = message.get('from', {}).get('first_name', 'Пользователь')
            text = message.get('text', '')
            
            if text == '/start':
                await bot.handle_start(chat_id, user_name)
        
        # Обработка callback queries
        elif 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['message']['chat']['id']
            callback_data = callback['data']
            
            if callback_data == 'marketplace_skills':
                await bot.handle_marketplace_skills(chat_id)
            elif callback_data == 'skills_categories':
                await bot.handle_skills_categories(chat_id)
            elif callback_data == 'start':
                user_name = callback.get('from', {}).get('first_name', 'Пользователь')
                await bot.handle_start(chat_id, user_name)
            else:
                await bot.send_message(chat_id, f"🔧 Функция '{callback_data}' в разработке")
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    """Главная страница бота"""
    return {
        "status": "running",
        "bot": "IA-Mother",
        "version": "1.0.0",
        "core_api": bot.core_api_url
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}

async def set_webhook():
    """Установка webhook для бота"""
    webhook_url = "https://your-domain.com/webhook"  # Замените на ваш домен
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            json={"url": webhook_url}
        )
        logger.info(f"Webhook установлен: {response.json()}")

if __name__ == "__main__":
    logger.info("🚀 Запуск Simple IA-Mother бота...")
    logger.info(f"📱 Токен: {TELEGRAM_BOT_TOKEN[:10]}...")
    logger.info(f"🌐 Core API: {bot.core_api_url}")
    
    # Для локального тестирования запускаем только FastAPI сервер
    # В продакшене нужно настроить webhook
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")