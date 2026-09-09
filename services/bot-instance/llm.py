"""
LLM and Core API clients for Zero Bot instances.

Split out of bot.py to keep the runtime module focused on Telegram wiring.
"""

from __future__ import annotations

import os

import httpx
from loguru import logger

# ── LLM config ──
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash-0731")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# Core API endpoint for error reporting.
CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
# Shared secret for Core API. Without it every call comes back 401.
CORE_API_TOKEN = os.getenv("CORE_API_TOKEN", "")
BOT_ID = os.getenv("BOT_ID", "zero-bot")


class LLMClient:
    """
    Multi-provider LLM client with fallback chain.
    Priority: OpenRouter → Anthropic → OpenAI
    """

    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None

    async def call(
        self,
        system_prompt: str,
        messages: list[dict],
        fallback: str = "Sorry, I couldn't process that.",
    ) -> str:
        """Call first available LLM provider."""
        # Try OpenRouter first
        if OPENROUTER_API_KEY:
            result = await self._call_openrouter(system_prompt, messages)
            if result:
                return result

        # Try Anthropic
        if ANTHROPIC_API_KEY:
            result = await self._call_anthropic(system_prompt, messages)
            if result:
                return result

        # Try OpenAI
        if OPENAI_API_KEY:
            result = await self._call_openai(system_prompt, messages)
            if result:
                return result

        return fallback

    async def _call_openrouter(self, system_prompt: str, messages: list[dict]) -> str | None:
        try:
            from openai import AsyncOpenAI
            if not self._openai_client:
                self._openai_client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY,
                )
            r = await self._openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system_prompt}] + messages,
                max_tokens=LLM_MAX_TOKENS,
            )
            content = (r.choices[0].message.content or "").strip()
            return content if content else None
        except Exception as e:
            logger.warning("OpenRouter failed: {}", e)
            return None

    async def _call_anthropic(self, system_prompt: str, messages: list[dict]) -> str | None:
        try:
            from anthropic import AsyncAnthropic
            if not self._anthropic_client:
                self._anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
            r = await self._anthropic_client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                max_tokens=LLM_MAX_TOKENS,
                system=system_prompt,
                messages=api_messages,
            )
            content = (r.content[0].text if r.content else "").strip()
            return content if content else None
        except Exception as e:
            logger.warning("Anthropic failed: {}", e)
            return None

    async def _call_openai(self, system_prompt: str, messages: list[dict]) -> str | None:
        try:
            from openai import AsyncOpenAI
            if not self._openai_client:
                self._openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            r = await self._openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": system_prompt}] + messages,
                max_tokens=LLM_MAX_TOKENS,
            )
            content = (r.choices[0].message.content or "").strip()
            return content if content else None
        except Exception as e:
            logger.warning("OpenAI failed: {}", e)
            return None


class CoreAPIClient:
    """Client for reporting errors and stats to Core API."""

    def __init__(self, base_url: str = CORE_API_URL):
        self.base_url = base_url
        self.headers = {"X-Core-API-Token": CORE_API_TOKEN} if CORE_API_TOKEN else {}

    async def report_error(
        self,
        bot_id: str,
        user_id: int | None,
        error_type: str,
        message: str,
        traceback_str: str = "",
        context: dict | None = None,
    ):
        """Submit error log to Core API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.base_url}/api/v1/feedback/error-logs/",
                    headers=self.headers,
                    json={
                        "bot_id": bot_id,
                        "user_id": user_id,
                        "error_type": error_type,
                        "message": message,
                        "traceback": traceback_str,
                        "context": context or {},
                    },
                )
        except Exception as e:
            logger.warning("Failed to report error to Core API: {}", e)

    async def submit_bug(
        self,
        user_id: int,
        title: str,
        description: str,
        logs: str | None = None,
    ):
        """Submit bug report."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.base_url}/api/v1/feedback/bug/",
                    headers=self.headers,
                    json={
                        "user_id": user_id,
                        "bot_id": BOT_ID,
                        "title": title,
                        "description": description,
                        "logs": logs,
                    },
                )
        except Exception as e:
            logger.warning("Failed to submit bug: {}", e)


def has_any_provider() -> bool:
    """True if at least one LLM provider key is configured."""
    return bool(OPENROUTER_API_KEY or ANTHROPIC_API_KEY or OPENAI_API_KEY)
