"""
Core API client for IA-Mother: marketplace, skills, bots, balance, exchange.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

import config

# Stub data for when API is unavailable
STUB_BOTS = [
    {"id": "1", "name": "Помощник Программиста", "creator": "@developer123", "price": "50", "rating": "4.8", "reviews": "127"},
    {"id": "2", "name": "Учитель Английского", "creator": "@teacher_ai", "price": "30", "rating": "4.9", "reviews": "89"},
]

STUB_SKILLS = [
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
        "created_at": "2024-01-15T10:30:00Z",
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
        "created_at": "2024-01-10T14:20:00Z",
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
        "created_at": "2024-02-01T09:15:00Z",
    },
]

STUB_CATEGORIES = [
    {"id": 1, "name": "Разработка", "icon": "💻", "skills_count": 45},
    {"id": 2, "name": "Языки", "icon": "🌍", "skills_count": 23},
    {"id": 3, "name": "Анализ", "icon": "📊", "skills_count": 18},
    {"id": 4, "name": "Творчество", "icon": "🎨", "skills_count": 12},
    {"id": 5, "name": "Утилиты", "icon": "🛠️", "skills_count": 31},
]

STUB_PLATFORM_STATS = {
    "total_bots": "1,247",
    "total_users": "5,892",
    "total_skills": "156",
    "total_personalities": "89",
    "ia_coins_supply": "1,250,000",
    "nft_passports": "1,247",
    "trading_volume": "45,892",
    "new_bots_24h": "23",
    "messages_24h": "15,678",
    "transactions_24h": "234",
}


class CoreAPI:
    """Client for Core API: marketplace, skills, bots, balance, exchange."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or config.CORE_API_URL) or ""

    async def get_marketplace_bots(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/marketplace/bots/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения ботов: {e}")
        return STUB_BOTS

    async def get_marketplace_skills(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/skills/skills/")
                if r.status_code == 200:
                    return r.json().get("results", [])
        except Exception as e:
            logger.error(f"Ошибка получения навыков: {e}")
        return STUB_SKILLS

    async def get_skill_categories(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/skills/categories/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения категорий: {e}")
        return STUB_CATEGORIES

    async def get_featured_skills(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/skills/skills/featured/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения популярных навыков: {e}")
        skills = await self.get_marketplace_skills()
        return sorted(skills, key=lambda x: x["popularity_score"], reverse=True)

    async def get_skill_details(self, skill_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/skills/skills/{skill_id}/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения навыка {skill_id}: {e}")
        skills = await self.get_marketplace_skills()
        for skill in skills:
            if skill["id"] == skill_id:
                skill = dict(skill)
                skill.update(
                    ratings_count=23,
                    requirements=["Python 3.8+", "API ключ"],
                    capabilities=["text_processing", "code_generation"],
                    config_schema={"api_key": {"type": "string", "required": True}, "temperature": {"type": "float", "default": 0.7}},
                )
                return skill
        return None

    async def get_bot_details(self, bot_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/bot-core/bot-passports/{bot_id}/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения бота {bot_id}: {e}")
        return {"id": bot_id, "name": f"Бот {bot_id[:8]}", "level": 5, "status": "active"}

    async def get_user_token(self, user_id: int) -> str:
        # TODO: real JWT for user
        return f"mock_token_for_user_{user_id}"

    async def install_skill_on_bot(
        self, skill_id: str, bot_id: str, user_id: int
    ) -> Dict[str, Any]:
        try:
            token = await self.get_user_token(user_id)
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self.base_url}/api/v1/skills/skills/{skill_id}/install/",
                    json={"bot_passport_id": bot_id, "config": {}},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if r.status_code == 201:
                    data = r.json()
                    return {
                        "success": True,
                        "installation_id": data.get("id"),
                        "skill_name": data.get("skill", {}).get("name", "Unknown"),
                        "bot_name": data.get("bot_passport_name", "Unknown"),
                        "price_paid": data.get("price_paid", "0.00"),
                    }
                err = r.json()
                return {"success": False, "error": err.get("error", "Неизвестная ошибка")}
        except Exception as e:
            logger.error(f"Ошибка установки навыка: {e}")
            return {"success": False, "error": f"Техническая ошибка: {str(e)}"}

    async def get_user_balance(self, user_id: int) -> Dict[str, str]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/users/{user_id}/balance/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
        return {"stars": "1000", "ia_coins": "10.50"}

    async def get_user_bots(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/users/{user_id}/bots/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения ботов пользователя: {e}")
        return [
            {"id": "bot_1", "name": "Мой Помощник", "status": "active", "level": "5", "message_count": "1,247", "revenue": "125.50"},
        ]

    async def get_platform_stats(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/stats/")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
        return dict(STUB_PLATFORM_STATS)

    async def get_exchange_rates(self) -> Optional[Dict[str, Decimal]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/v1/exchange/rates/")
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "stars_to_ia_coin": Decimal(str(data.get("stars_to_ia_coin", "0.01"))),
                        "ia_coin_to_stars": Decimal(str(data.get("ia_coin_to_stars", "100"))),
                    }
        except Exception as e:
            logger.error(f"Ошибка получения курсов: {e}")
        return None

    async def process_exchange(
        self,
        user_id: int,
        from_currency: str,
        to_currency: str,
        amount: Decimal,
        rates: Dict[str, Decimal],
    ) -> Dict[str, Any]:
        try:
            balance = await self.get_user_balance(user_id)
            if from_currency == "stars":
                if Decimal(balance["stars"]) < amount:
                    return {"success": False, "error": "Недостаточно Stars"}
                ia_coins_amount = amount * rates["stars_to_ia_coin"]
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{self.base_url}/api/v1/exchange/",
                        json={
                            "user_id": user_id,
                            "from_currency": "stars",
                            "to_currency": "ia_coins",
                            "from_amount": str(amount),
                            "to_amount": str(ia_coins_amount),
                            "rate": str(rates["stars_to_ia_coin"]),
                        },
                    )
                    if r.status_code == 200:
                        return {
                            "success": True,
                            "from_amount": amount,
                            "to_amount": ia_coins_amount,
                            "rate": rates["stars_to_ia_coin"],
                        }
            return {"success": False, "error": "Ошибка обработки"}
        except Exception as e:
            logger.error(f"Ошибка обмена: {e}")
            return {"success": False, "error": str(e)}
