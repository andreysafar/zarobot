"""
Zero Bot Instance — Tamagotchi AI Bot
Each bot runs in its own container with a personality and skills.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from telethon import TelegramClient, events

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BOT_ID = os.getenv("BOT_ID", "unknown")
OWNER_TELEGRAM_ID = int(os.getenv("OWNER_TELEGRAM_ID", "0"))
REDIS_URL = os.getenv("REDIS_URL", "")
LANGFLOW_API_URL = os.getenv("LANGFLOW_API_URL", "")

DATA_DIR = Path("/data")
PERSONALITY_DIR = DATA_DIR / "personality"
SKILLS_DIR = DATA_DIR / "skills"
STATE_FILE = DATA_DIR / "state" / "state.json"


class PersonalityLoader:
    """Loads personality from manifest + prompt files."""

    def __init__(self, personality_dir: Path):
        self.dir = personality_dir
        self.manifest: dict = {}
        self.system_prompt = ""
        self.system_prompt_free = ""
        self.greeting_template = ""
        self.fallback = ""
        self._load()

    def _load(self):
        manifest_path = self.dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning("No personality manifest found, using defaults")
            return

        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        prompts_cfg = self.manifest.get("prompts", {})

        for attr, key in [
            ("system_prompt", "system"),
            ("system_prompt_free", "system_free"),
            ("greeting_template", "greeting"),
            ("fallback", "fallback"),
        ]:
            path = self.dir / prompts_cfg.get(key, "")
            if path.exists():
                setattr(self, attr, path.read_text(encoding="utf-8").strip())

    def get_greeting(self, user_name: str, bot_name: str) -> str:
        if self.greeting_template:
            try:
                return self.greeting_template.format(user_name=user_name, bot_name=bot_name)
            except KeyError:
                return self.greeting_template
        return f"Привет, {user_name}! Я {bot_name} 👋"

    @property
    def display_name(self) -> str:
        return self.manifest.get("display_name", "Zero Bot")

    @property
    def ai_model(self) -> dict:
        return self.manifest.get("ai_model", {})

    @property
    def behavior(self) -> dict:
        return self.manifest.get("behavior", {})


class BotState:
    """Persistent bot state: XP, level, stats."""

    def __init__(self, state_file: Path):
        self.file = state_file
        self.xp = 0
        self.level = 0
        self.messages_total = 0
        self.created_at = datetime.utcnow().isoformat()
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
        self.file.write_text(json.dumps({
            "xp": self.xp,
            "level": self.level,
            "messages_total": self.messages_total,
            "created_at": self.created_at,
        }, indent=2))

    def add_xp(self, points: int = 1):
        self.xp += points
        self.messages_total += 1
        new_level = self.xp // 100
        if new_level > self.level:
            self.level = new_level
            logger.info(f"Level up! Now level {self.level}")
        self.save()


class ZeroBotInstance:
    """Individual Zero Bot instance — one per Docker container."""

    def __init__(self):
        self.personality = PersonalityLoader(PERSONALITY_DIR)
        self.state = BotState(STATE_FILE)
        self.conversations: dict[int, list[dict]] = {}

        self.client = TelegramClient(
            f"/data/state/bot_{BOT_ID}",
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        )

        logger.info(f"Bot {BOT_ID} initialized | personality={self.personality.display_name}")

    async def start(self):
        await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)
        self._register_handlers()
        logger.info(f"Bot {BOT_ID} started | level={self.state.level} xp={self.state.xp}")
        await self.client.run_until_disconnected()

    def _register_handlers(self):

        @self.client.on(events.NewMessage(pattern="/start"))
        async def on_start(event):
            sender = await event.get_sender()
            name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
            greeting = self.personality.get_greeting(
                user_name=name,
                bot_name=self.personality.display_name,
            )
            await event.respond(greeting)

        @self.client.on(events.NewMessage(pattern="/stats"))
        async def on_stats(event):
            await event.respond(
                f"📊 **{self.personality.display_name}**\n\n"
                f"Level: {self.state.level}\n"
                f"XP: {self.state.xp}\n"
                f"Messages: {self.state.messages_total}\n"
                f"Created: {self.state.created_at[:10]}"
            )

        @self.client.on(events.NewMessage(pattern="/help"))
        async def on_help(event):
            await event.respond(
                f"🤖 **{self.personality.display_name}**\n\n"
                "Команды:\n"
                "/start — Приветствие\n"
                "/stats — Статистика бота\n"
                "/help — Помощь\n\n"
                "Просто пишите — я отвечу!"
            )

        @self.client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith("/")))
        async def on_message(event):
            sender = await event.get_sender()
            text = event.text

            try:
                response = await self._process_message(text, sender)
                await event.respond(response)
                self.state.add_xp(1)
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                if self.personality.fallback:
                    await event.respond(self.personality.fallback)

    async def _process_message(self, text: str, sender: Any) -> str:
        """Process message through Langflow or fallback to echo."""
        if LANGFLOW_API_URL:
            try:
                return await self._langflow_respond(text, sender)
            except Exception as e:
                logger.warning(f"Langflow unavailable: {e}")

        return f"Я получил: «{text}»\n\n(AI модель ещё не подключена. Настройте Langflow.)"

    async def _langflow_respond(self, text: str, sender: Any) -> str:
        flow_id = os.getenv("LANGFLOW_FLOW_ID", "")
        if not flow_id:
            raise ValueError("LANGFLOW_FLOW_ID not set")

        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{LANGFLOW_API_URL}/api/v1/run/{flow_id}",
                json={
                    "input_value": text,
                    "tweaks": {
                        "system_prompt": self.personality.system_prompt,
                        "bot_name": self.personality.display_name,
                        "user_name": getattr(sender, "first_name", "User"),
                    },
                },
            )
            resp.raise_for_status()
            return resp.json().get("output", self.personality.fallback)


async def main():
    bot = ZeroBotInstance()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
