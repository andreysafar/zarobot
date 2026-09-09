"""
Persistent state for Zero Bot instances: XP/level and conversation history.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger


class BotState:
    """Persistent bot state: XP, level, stats."""

    def __init__(self, state_file: Path):
        self.file = state_file
        self.xp = 0
        self.level = 0
        self.messages_total = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._load()

    def _load(self):
        if self.file.exists():
            data = json.loads(self.file.read_text())
            self.xp = data.get("xp", 0)
            self.level = data.get("level", 0)
            self.messages_total = data.get("messages_total", 0)
            self.created_at = data.get("created_at", self.created_at)

    def save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(
            json.dumps(
                {
                    "xp": self.xp,
                    "level": self.level,
                    "messages_total": self.messages_total,
                    "created_at": self.created_at,
                },
                indent=2,
            )
        )

    def add_xp(self, points: int = 1):
        self.xp += points
        self.messages_total += 1
        new_level = self.xp // 100
        if new_level > self.level:
            self.level = new_level
            logger.info("Level up! Now level {}", self.level)
        self.save()


class ConversationManager:
    """Manages per-user conversation history."""

    def __init__(self, conversation_file: Path, max_history: int = 20):
        self.file = conversation_file
        self.max_history = max_history
        self._conversations: dict[int, list[dict]] = {}
        self._load()

    def _load(self):
        if self.file.exists():
            try:
                data = json.loads(self.file.read_text())
                self._conversations = {int(k): v for k, v in data.items()}
            except (json.JSONDecodeError, ValueError):
                self._conversations = {}

    def save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self._conversations, ensure_ascii=False, indent=2))

    def get_history(self, user_id: int) -> list[dict]:
        return self._conversations.get(user_id, [])

    def add_message(self, user_id: int, role: str, content: str):
        if user_id not in self._conversations:
            self._conversations[user_id] = []
        self._conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Trim history
        if len(self._conversations[user_id]) > self.max_history:
            self._conversations[user_id] = self._conversations[user_id][-self.max_history:]
        self.save()

    def clear_history(self, user_id: int):
        self._conversations.pop(user_id, None)
        self.save()

