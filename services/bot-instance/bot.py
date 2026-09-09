"""
Zero Bot Instance — Production-ready AI bot template.
Each bot runs in its own container with:
  - Personality (prompts + manifest)
  - LLM integration (OpenRouter → OpenAI → Anthropic)
  - Langflow flows (optional)
  - Skill system (modular abilities)
  - Error reporting to Core API
  - Conversation history + XP/level system

This is the template that IA-Mother clones to create new bots.
"""

import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from telethon import TelegramClient, events

try:
    from . import handlers as h
    from .group_gate import decide as gate_decide
    from .llm import CoreAPIClient, LLMClient, LLM_MODEL, has_any_provider
    from .skill_loader import SkillManager
    from .state import BotState, ConversationManager
except ImportError:
    import handlers as h
    from group_gate import decide as gate_decide
    from llm import CoreAPIClient, LLMClient, LLM_MODEL, has_any_provider
    from skill_loader import SkillManager
    from state import BotState, ConversationManager

# ── Environment ──
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BOT_ID = os.getenv("BOT_ID", "zero-bot")
BOT_NAME = os.getenv("BOT_NAME", "Zero Bot")
CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
LANGFLOW_API_URL = os.getenv("LANGFLOW_API_URL", "")
LANGFLOW_FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "")
REDIS_URL = os.getenv("REDIS_URL", "")
PERSONALITY_ID = os.getenv("PERSONALITY", "ia")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
# Restrict ingest / answering to these chats when set (comma separated).
ALLOWED_CHAT_IDS = {
    int(c) for c in os.getenv("ALLOWED_CHAT_IDS", "").replace(" ", "").split(",") if c
}

DATA_DIR = Path("/data")
PERSONALITY_ROOT = DATA_DIR / "personality"
SKILLS_DIR = DATA_DIR / "skills"
STATE_FILE = DATA_DIR / "state" / "state.json"
CONVERSATION_FILE = DATA_DIR / "state" / "conversations.json"


class PersonalityLoader:
    """Loads personality from manifest + prompt files.

    The image ships every personality under /data/personality/<id>/ (e.g. `ia`),
    but some deployments flatten a single personality directly into
    /data/personality/. Both layouts are resolved here.
    """

    def __init__(self, personality_root: Path, personality_id: str = ""):
        self.root = personality_root
        self.personality_id = personality_id
        self.dir = self._resolve_dir(personality_root, personality_id)
        self.manifest: dict = {}
        self.system_prompt = ""
        self.system_prompt_free = ""
        self.greeting_template = ""
        self.fallback = ""
        self._load()

    @staticmethod
    def _resolve_dir(root: Path, personality_id: str) -> Path:
        """Pick `<root>/<id>` when present, else `<root>` itself.

        Only a directory that actually holds a manifest is accepted. When
        neither layout has one we still return the most specific candidate —
        `_load` then degrades to defaults rather than reading a directory as
        if it were a file.
        """
        candidates = []
        if personality_id:
            candidates.append(root / personality_id)
        candidates.append(root)

        for candidate in candidates:
            if (candidate / "manifest.json").is_file():
                return candidate
        return candidates[0]

    def _load(self):
        manifest_path = self.dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning(
                "No personality manifest at {}, using defaults", manifest_path
            )
            self.system_prompt = "You are a helpful AI assistant."
            self.fallback = "I'm not sure how to help with that. Could you rephrase?"
            return

        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        prompts_cfg = self.manifest.get("prompts", {})
        for attr, key in [
            ("system_prompt", "system"),
            ("system_prompt_free", "system_free"),
            ("greeting_template", "greeting"),
            ("fallback", "fallback"),
        ]:
            rel = prompts_cfg.get(key, "")
            if not rel:
                continue
            path = self.dir / rel
            if path.is_file():
                setattr(self, attr, path.read_text(encoding="utf-8").strip())

    def prompt(self, key: str) -> str:
        """Read an auxiliary prompt by manifest key (e.g. 'summary_agent')."""
        rel = self.manifest.get("prompts", {}).get(key, "")
        if not rel:
            return ""
        path = self.dir / rel
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def get_greeting(self, user_name: str, bot_name: str) -> str:
        if self.greeting_template:
            try:
                return self.greeting_template.format(user_name=user_name, bot_name=bot_name)
            except KeyError:
                return self.greeting_template
        return f"Привет, {user_name}! Я {bot_name} 👋"

    @property
    def display_name(self) -> str:
        return self.manifest.get("display_name", BOT_NAME)

    @property
    def ai_model(self) -> dict:
        return self.manifest.get("ai_model", {})

    @property
    def behavior(self) -> dict:
        return self.manifest.get("behavior", {})

    @property
    def features(self) -> dict:
        return self.manifest.get("features", {})

    @property
    def activation_phrase(self) -> str | None:
        """Word that addresses the bot in a group (e.g. 'ия')."""
        return self.behavior.get("activation_phrase") or None



class ZeroBotInstance:
    """
    Individual Zero Bot instance — one per Docker container.
    This is the template that IA-Mother clones.
    """

    def __init__(self):
        self.personality = PersonalityLoader(PERSONALITY_ROOT, PERSONALITY_ID)
        self.state = BotState(STATE_FILE)
        self.conversations = ConversationManager(CONVERSATION_FILE)
        self.llm = LLMClient()
        self.core_api = CoreAPIClient()
        self.skills = SkillManager(SKILLS_DIR)
        self.bot_username: str | None = None
        self._bot_user_id: int | None = None
        self.client = TelegramClient(
            f"/data/state/bot_{BOT_ID}",
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        )
        logger.info(
            "Bot {} initialized | personality={} ({})",
            BOT_ID, self.personality.display_name, self.personality.dir,
        )

    async def _delete_webhook(self):
        """Remove webhook so this process receives updates."""
        if not TELEGRAM_BOT_TOKEN:
            return
        try:
            async with httpx.AsyncClient() as http:
                r = await http.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook")
                if r.json().get("ok"):
                    logger.info("Webhook removed")
        except Exception as e:
            logger.warning("Could not delete webhook: {}", e)

    async def start(self):
        await self._delete_webhook()
        await self.client.start(bot_token=TELEGRAM_BOT_TOKEN)

        me = await self.client.get_me()
        self.bot_username = getattr(me, "username", None)
        self._bot_user_id = getattr(me, "id", None)

        # Skills must be loaded before handlers register, so dispatch can see
        # the command table.
        self.skills.load()
        await self.skills.install_all(self._make_skill_context(chat_id=0, user_id=0))

        self._register_handlers()
        logger.info(
            "Bot {} started as @{} | personality={} | skills={} | level={} xp={}",
            BOT_ID, self.bot_username, self.personality.personality_id or "default",
            [s.name for s in self.skills.skills], self.state.level, self.state.xp,
        )
        await self.client.run_until_disconnected()

    def _register_handlers(self):
        """Register a single group-aware entry point.

        One handler owns all text traffic so gating lives in exactly one place;
        per-command handlers are not registered here because the gate decides.
        """
        bot = self

        @self.client.on(events.NewMessage(func=lambda e: bool(e.text)))
        async def on_message(event):
            await bot.handle_event(event)

    # ── Group-aware dispatch ──

    async def handle_event(self, event) -> None:
        """Single entry point for every incoming text message."""
        sender = await event.get_sender()
        text = event.text or ""
        chat_id = getattr(event, "chat_id", None) or getattr(sender, "id", 0)
        is_private = bool(getattr(event, "is_private", False))

        if ALLOWED_CHAT_IDS and not is_private and chat_id not in ALLOWED_CHAT_IDS:
            return

        decision = gate_decide(
            text,
            is_private=is_private,
            bot_username=self.bot_username,
            activation_phrase=self.personality.activation_phrase,
            is_reply_to_bot=await self._is_reply_to_bot(event),
        )
        if not decision.should_handle:
            logger.debug("Ignoring chatter in chat {}: {!r}", chat_id, text[:60])
            return

        if decision.is_command:
            await self._dispatch_command(event, decision, sender, chat_id)
            return

        await self._dispatch_message(event, decision, sender, chat_id, is_private)

    async def _is_reply_to_bot(self, event) -> bool:
        """True if this message replies to a message sent by us."""
        if not self._bot_user_id or not getattr(event, "is_reply", False):
            return False
        try:
            replied = await event.get_reply_message()
        except Exception:
            return False
        return bool(replied) and getattr(replied, "sender_id", None) == self._bot_user_id

    async def _dispatch_command(self, event, decision, sender, chat_id: int) -> None:
        """Route a slash command: skill first, then built-in handlers."""
        parsed = decision.parsed
        skill = self.skills.get_skill_for_command("/" + parsed.command)

        if skill is not None:
            ctx = self._make_skill_context(chat_id, getattr(sender, "id", 0))
            ctx.config = {**skill.config, "is_private": event.is_private}
            try:
                response = await skill.instance.on_command(ctx, "/" + parsed.command, parsed.args)
            except Exception as e:
                logger.error("Skill {} failed on /{}: {}", skill.name, parsed.command, e)
                await self.core_api.report_error(
                    bot_id=BOT_ID,
                    user_id=getattr(sender, "id", 0),
                    error_type="skill_error",
                    message=str(e),
                    traceback_str=traceback.format_exc(),
                    context={"skill": skill.name, "command": parsed.command},
                )
                response = None

            if response is not None and response.has_content() and not response.is_skip():
                await self._send_skill_response(event, response)
                return
            if response is not None and response.is_consume():
                return
            # Skill skipped — fall through to built-in commands.

        await h.handle_builtin_command(event, self, parsed.command, parsed.args)

    async def _dispatch_message(self, event, decision, sender, chat_id, is_private) -> None:
        """Route a plain message through the skill chain, then the personality."""
        text = decision.clean_text or event.text
        ctx = self._make_skill_context(chat_id, getattr(sender, "id", 0))
        ctx.config["is_private"] = is_private

        for skill in self.skills.skills:
            try:
                response = await skill.instance.on_message(ctx, text)
            except Exception as e:
                logger.error("Skill {} failed on message: {}", skill.name, e)
                await self.core_api.report_error(
                    bot_id=BOT_ID,
                    user_id=getattr(sender, "id", 0),
                    error_type="skill_error",
                    message=str(e),
                    traceback_str=traceback.format_exc(),
                    context={"skill": skill.name, "message_text": text[:200]},
                )
                continue

            if response is None or response.is_skip():
                continue
            if response.is_consume():
                return
            if response.has_content():
                await self._send_skill_response(event, response)
                return

        # No skill answered — the personality only speaks when addressed, or in DM.
        if is_private or decision.trigger.value in ("mention", "reply"):
            await h.handle_message(event, self, text)
            return

        if decision.needs_retrieval_check:
            # A bare question in a group: only worth answering if some skill
            # produced content. Otherwise stay silent instead of spamming.
            logger.debug("Question in chat {} left unanswered — no skill content", chat_id)
            return

    async def _send_skill_response(self, event, response) -> None:
        """Send a SkillResponse, including inline buttons when present."""
        if response.buttons:
            await event.respond(response.text or "", buttons=response.buttons)
        else:
            await event.respond(response.text or "")
        self.state.add_xp(1)

    def _make_skill_context(self, chat_id: int, user_id: int):
        """Build a SkillContext for skill invocations."""
        from zero_bot_sdk import SkillContext

        return SkillContext(
            bot_id=BOT_ID,
            user_id=user_id,
            chat_id=chat_id,
            config={},
            bot_level=self.state.level,
            bot_xp=self.state.xp,
            conversation=self.conversations.get_history(user_id),
        )

    async def _process_message(self, text: str, sender: Any, chat_id: int = 0) -> str:
        """
        Main message processing pipeline:
        1. Try Langflow (if configured)
        2. Fall back to direct LLM call
        3. Update conversation history
        """
        sender_id = getattr(sender, "id", 0)
        sender_name = getattr(sender, "first_name", None) or getattr(sender, "username", "User")
        # In groups the shared thread is the chat; in DMs it is the user.
        history_key = chat_id if chat_id else sender_id

        # Build conversation context
        history = self.conversations.get_history(history_key)
        messages = [{"role": m["role"], "content": m["content"]} for m in history[-10:]]

        # Add current message
        messages.append({"role": "user", "content": text})

        # Try Langflow first
        if LANGFLOW_API_URL and LANGFLOW_FLOW_ID:
            try:
                response = await self._langflow_respond(text, sender_name)
                if response:
                    self.conversations.add_message(history_key, "user", text)
                    self.conversations.add_message(history_key, "assistant", response)
                    return response
            except Exception as e:
                logger.warning("Langflow unavailable: {}", e)
                await self.core_api.report_error(
                    bot_id=BOT_ID,
                    user_id=sender_id,
                    error_type="langflow_error",
                    message=str(e),
                    traceback_str=traceback.format_exc(),
                )

        # Fall back to direct LLM
        system_prompt = self.personality.system_prompt
        fallback = self.personality.fallback or "Sorry, I couldn't process that. Please try again."

        try:
            response = await self.llm.call(system_prompt, messages, fallback)
            self.conversations.add_message(history_key, "user", text)
            self.conversations.add_message(history_key, "assistant", response)
            return response
        except Exception as e:
            logger.error("LLM call failed: {}", e)
            await self.core_api.report_error(
                bot_id=BOT_ID,
                user_id=sender_id,
                error_type="llm_error",
                message=str(e),
                traceback_str=traceback.format_exc(),
                context={"model": LLM_MODEL},
            )
            return fallback

    async def _langflow_respond(self, text: str, sender_name: str) -> str | None:
        """Call Langflow flow API."""
        if not LANGFLOW_API_URL or not LANGFLOW_FLOW_ID:
            return None

        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{LANGFLOW_API_URL}/api/v1/run/{LANGFLOW_FLOW_ID}",
                json={
                    "input_value": text,
                    "tweaks": {
                        "system_prompt": self.personality.system_prompt,
                        "bot_name": self.personality.display_name,
                        "user_name": sender_name,
                    },
                },
            )
            resp.raise_for_status()
            result = resp.json()
            output = result.get("output", "")
            if isinstance(output, dict):
                return output.get("text", "") or str(output)
            return str(output) if output else None


async def main():
    if not has_any_provider() and not (LANGFLOW_API_URL and LANGFLOW_FLOW_ID):
        # Without a key every answer silently falls back — make that obvious.
        logger.warning(
            "No LLM provider configured (OPENROUTER/ANTHROPIC/OPENAI) and no "
            "Langflow flow — the bot will only return fallback text."
        )
    bot = ZeroBotInstance()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
