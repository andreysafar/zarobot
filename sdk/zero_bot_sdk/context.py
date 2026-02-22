"""Contexts passed to skill and personality handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Storage:
    """Per-skill, per-bot persistent key-value storage backed by Redis."""

    _data: dict[str, Any] = field(default_factory=dict)
    _redis: Any = None
    _prefix: str = ""

    async def get(self, key: str, default: Any = None) -> Any:
        if self._redis:
            val = await self._redis.get(f"{self._prefix}:{key}")
            return val if val is not None else default
        return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        if self._redis:
            await self._redis.set(f"{self._prefix}:{key}", value)
        else:
            self._data[key] = value

    async def delete(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(f"{self._prefix}:{key}")
        else:
            self._data.pop(key, None)


@dataclass
class SkillContext:
    """Context passed to every skill handler invocation."""

    bot_id: str
    user_id: int
    chat_id: int
    config: dict[str, Any]
    bot_level: int = 0
    bot_xp: int = 0
    conversation: list[dict] = field(default_factory=list)
    storage: Storage = field(default_factory=Storage)
    redis: Any = None
    langflow: Any = None

    @classmethod
    def for_testing(cls, **overrides) -> "SkillContext":
        defaults = {
            "bot_id": "test-bot-001",
            "user_id": 123456,
            "chat_id": 123456,
            "config": {},
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class PersonalityContext:
    """Context passed to personality handler."""

    bot_id: str
    user_id: int
    chat_id: int
    user_name: str = ""
    bot_name: str = ""
    bot_level: int = 0
    conversation: list[dict] = field(default_factory=list)
    storage: Storage = field(default_factory=Storage)
    redis: Any = None
    langflow: Any = None
