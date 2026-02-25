"""LLM calls for test_zero_local: OpenRouter, OpenAI, Anthropic."""

import os
import logging

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


async def call_llm(system_prompt: str, messages: list, fallback: str) -> str:
    """Call first available provider; return fallback on failure."""
    if OPENROUTER_API_KEY and AsyncOpenAI:
        try:
            client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
            r = await client.chat.completions.create(
                model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001"),
                messages=[{"role": "system", "content": system_prompt}] + messages,
                max_tokens=1024,
            )
            return (r.choices[0].message.content or "").strip() or fallback
        except Exception as e:
            logger.exception("OpenRouter error: %s", e)
    if OPENAI_API_KEY and AsyncOpenAI:
        try:
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            r = await client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": system_prompt}] + messages,
                max_tokens=1024,
            )
            return (r.choices[0].message.content or "").strip() or fallback
        except Exception as e:
            logger.exception("OpenAI error: %s", e)
    if ANTHROPIC_API_KEY and AsyncAnthropic:
        try:
            client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
            r = await client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
                max_tokens=1024,
                system=system_prompt,
                messages=api_messages,
            )
            return (r.content[0].text if r.content else "").strip() or fallback
        except Exception as e:
            logger.exception("Anthropic error: %s", e)
    return fallback
