"""
Core API client for IA-Mother: marketplace, skills, bots, balance, exchange.
Uses retry with exponential backoff. Returns error dicts instead of stub data.
"""

import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

import config


class CoreAPIError(Exception):
    """Raised when Core API is unavailable after retries."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CoreAPI:
    """Client for Core API: marketplace, skills, bots, balance, exchange."""

    def __init__(self, base_url: str | None = None, max_retries: int = 3):
        self.base_url = (base_url or config.CORE_API_URL) or ""
        self.max_retries = max_retries
        # Shared secret for Core API; without it every call comes back 401.
        token = os.getenv("CORE_API_TOKEN", "")
        self.auth_headers = {"X-Core-API-Token": token} if token else {}

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        """
        Make an HTTP request to Core API with retry logic.
        Raises CoreAPIError if all retries fail.
        """
        # Auth header goes on every request; caller-supplied headers win only
        # for keys they set themselves.
        headers = {**self.auth_headers, **(headers or {})}

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if method == "GET":
                        r = await client.get(f"{self.base_url}{path}", headers=headers)
                    elif method == "POST":
                        r = await client.post(f"{self.base_url}{path}", json=json, headers=headers)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                    if r.status_code < 500:
                        # 2xx/4xx — return parsed response
                        return r.json()

                    # 5xx — retry
                    last_error = f"HTTP {r.status_code}: {r.text[:200]}"
                    logger.warning(f"Core API attempt {attempt + 1}/{self.max_retries}: {last_error}")

            except httpx.ConnectError as e:
                last_error = f"Connection refused: {e}"
                logger.warning(f"Core API attempt {attempt + 1}/{self.max_retries}: {last_error}")
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning(f"Core API attempt {attempt + 1}/{self.max_retries}: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Core API attempt {attempt + 1}/{self.max_retries}: {last_error}")

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)

        raise CoreAPIError(
            f"Core API unavailable after {self.max_retries} attempts. Last error: {last_error}"
        )

    async def get_marketplace_bots(self) -> List[Dict[str, Any]]:
        try:
            data = await self._request("GET", "/api/v1/marketplace/bots/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get marketplace bots: {e}")
            raise

    async def get_marketplace_skills(self) -> List[Dict[str, Any]]:
        try:
            data = await self._request("GET", "/api/v1/skills/skills/")
            return data.get("results", [])
        except CoreAPIError as e:
            logger.error(f"Failed to get marketplace skills: {e}")
            raise

    async def get_skill_categories(self) -> List[Dict[str, Any]]:
        try:
            data = await self._request("GET", "/api/v1/skills/categories/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get skill categories: {e}")
            raise

    async def get_featured_skills(self) -> List[Dict[str, Any]]:
        try:
            data = await self._request("GET", "/api/v1/skills/skills/featured/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get featured skills: {e}")
            raise

    async def get_skill_details(self, skill_id: str) -> Dict[str, Any]:
        try:
            data = await self._request("GET", f"/api/v1/skills/skills/{skill_id}/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get skill {skill_id}: {e}")
            raise

    async def get_bot_details(self, bot_id: str) -> Dict[str, Any]:
        try:
            data = await self._request("GET", f"/api/v1/bot-core/bot-passports/{bot_id}/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get bot {bot_id}: {e}")
            raise

    async def install_skill_on_bot(
        self, skill_id: str, bot_id: str, user_id: int
    ) -> Dict[str, Any]:
        try:
            data = await self._request(
                "POST",
                f"/api/v1/skills/skills/{skill_id}/install/",
                # user_id обязателен: сервер по нему проверяет, что навык
                # ставит владелец бота, и с чьего кошелька списывать.
                json={"bot_passport_id": bot_id, "user_id": user_id, "config": {}},
            )
            return {
                "success": True,
                "installation_id": data.get("id"),
                "skill_name": data.get("skill_name", "Unknown"),
                "bot_name": data.get("bot_passport_name", "Unknown"),
                "price_paid": data.get("price_paid", "0.00"),
            }
        except CoreAPIError as e:
            logger.error(f"Failed to install skill: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_balance(self, user_id: int) -> Dict[str, str]:
        try:
            data = await self._request("GET", f"/api/v1/users/{user_id}/balance/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get balance for user {user_id}: {e}")
            raise

    async def get_user_bots(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            data = await self._request("GET", f"/api/v1/users/{user_id}/bots/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get bots for user {user_id}: {e}")
            raise

    async def get_platform_stats(self) -> Dict[str, Any]:
        try:
            data = await self._request("GET", "/api/v1/stats/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get platform stats: {e}")
            raise

    async def get_exchange_rates(self) -> Optional[Dict[str, Decimal]]:
        try:
            data = await self._request("GET", "/api/v1/exchange/rates/")
            return {
                "stars_to_ia_coin": Decimal(str(data.get("stars_to_ia_coin", "0.01"))),
                "ia_coin_to_stars": Decimal(str(data.get("ia_coin_to_stars", "100"))),
            }
        except CoreAPIError as e:
            logger.error(f"Failed to get exchange rates: {e}")
            return None

    async def process_exchange(
        self,
        user_id: int,
        from_currency: str,
        amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Обменять валюту.

        Курс и итоговую сумму считает сервер — клиент их не передаёт.
        Раньше здесь вычислялся to_amount и уходил на сервер как есть,
        то есть курс задавала сторона, которая за него не отвечает.
        """
        to_currency = "ia_coins" if from_currency == "stars" else "stars"
        try:
            data = await self._request(
                "POST",
                "/api/v1/exchange/",
                json={
                    "user_id": user_id,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "from_amount": float(amount),
                },
            )
        except CoreAPIError as e:
            return {"success": False, "error": str(e)}

        if not data.get("success"):
            return {"success": False, "error": data.get("detail", "Обмен не выполнен")}
        return {
            "success": True,
            "from_amount": data["from_amount"],
            "to_amount": data["to_amount"],
            "rate": data["rate"],
            "new_balance": data.get("new_balance", {}),
        }

    async def create_passport(
        self, owner_id: int, owner_telegram: str, name: str, personality: str = "ia"
    ) -> Dict[str, Any]:
        """Create a new bot passport."""
        try:
            data = await self._request(
                "POST",
                "/api/v1/bot-core/bot-passports/",
                json={
                    "owner_id": owner_id,
                    "owner_telegram": owner_telegram,
                    "name": name,
                    "personality": personality,
                },
            )
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to create passport: {e}")
            raise

    async def update_bot_container(self, bot_id: str, container_id: str) -> Dict[str, Any]:
        """Update bot passport with container ID."""
        try:
            data = await self._request(
                "PATCH",
                f"/api/v1/bot-core/bot-passports/{bot_id}/",
                json={"container_id": container_id},
            )
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to update bot container: {e}")
            raise

    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Get bot passport status."""
        try:
            data = await self._request("GET", f"/api/v1/bot-core/bot-passports/{bot_id}/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get bot status: {e}")
            return {"error": str(e)}

    async def submit_bug_report(
        self, user_id: int, title: str, description: str, bot_id: str = None, logs: str = None
    ) -> Dict[str, Any]:
        """Submit a bug report."""
        try:
            data = await self._request(
                "POST",
                "/api/v1/feedback/bug/",
                json={
                    "user_id": user_id,
                    "bot_id": bot_id,
                    "title": title,
                    "description": description,
                    "logs": logs,
                },
            )
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to submit bug report: {e}")
            raise

    async def get_platform_stats(self) -> Dict[str, Any]:
        """Get platform statistics."""
        try:
            data = await self._request("GET", "/api/v1/stats/")
            return data
        except CoreAPIError as e:
            logger.error(f"Failed to get platform stats: {e}")
            raise
