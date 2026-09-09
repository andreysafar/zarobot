"""End-to-end tests for the group-aware dispatch in bot.py.

These cover the behaviour CLAUDE.md calls out: the bot must not reply to
ordinary chatter in a group, and must route addressed messages through the
skill chain before falling back to the personality.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
BOT_MODULE = ROOT / "services" / "bot-instance" / "bot.py"


def _load_side_module(name: str):
    """Import a sibling module of bot.py (state.py, llm.py) by path."""
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", ROOT / "services" / "bot-instance" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{name}_under_test"] = module
    spec.loader.exec_module(module)
    return module
SKILL_TEMPLATE = '''
from zero_bot_sdk import BaseSkill, SkillResponse

class {cls}(BaseSkill):
    name = "{name}"

    async def on_command(self, ctx, command, args):
        if command == "/faq":
            return SkillResponse(text="FAQ: " + args)
        return SkillResponse.skip()

    async def on_message(self, ctx, text):
        if "деплой" in text.lower():
            return SkillResponse(text="Деплой описан в README.")
        return SkillResponse.skip()
'''


@pytest.fixture
def bot_module():
    """Import bot.py fresh, with a temp data dir and no network."""
    spec = importlib.util.spec_from_file_location("bot_dispatch_under_test", BOT_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot_dispatch_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def state_mod():
    return _load_side_module("state")


@pytest.fixture(scope="module")
def llm_mod():
    return _load_side_module("llm")


@pytest.fixture
def bot(bot_module, state_mod, llm_mod, tmp_path, monkeypatch):
    """A ZeroBotInstance with file paths redirected into tmp_path."""
    monkeypatch.setattr(bot_module, "STATE_FILE", tmp_path / "state" / "state.json")
    monkeypatch.setattr(bot_module, "CONVERSATION_FILE", tmp_path / "state" / "conversations.json")
    monkeypatch.setattr(bot_module, "PERSONALITY_ROOT", tmp_path / "personality")
    monkeypatch.setattr(bot_module, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(bot_module, "ALLOWED_CHAT_IDS", set())
    monkeypatch.setattr(bot_module, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(bot_module, "LANGFLOW_API_URL", "")
    monkeypatch.setattr(bot_module, "LANGFLOW_FLOW_ID", "")

    (tmp_path / "personality" / "ia").mkdir(parents=True)
    (tmp_path / "personality" / "ia" / "manifest.json").write_text(
        json.dumps(
            {
                "display_name": "Ия",
                "prompts": {},
                "behavior": {"activation_phrase": "ия"},
            }
        ),
        encoding="utf-8",
    )

    instance = bot_module.ZeroBotInstance.__new__(bot_module.ZeroBotInstance)
    instance.personality = bot_module.PersonalityLoader(tmp_path / "personality", "ia")
    instance.state = state_mod.BotState(tmp_path / "state" / "state.json")
    instance.conversations = state_mod.ConversationManager(
        tmp_path / "state" / "conversations.json"
    )
    instance.llm = llm_mod.LLMClient()
    instance.core_api = llm_mod.CoreAPIClient()
    instance.skills = bot_module.SkillManager(tmp_path / "skills")
    instance.bot_username = "my_helper_bot"
    instance._bot_user_id = 999
    return instance


def _add_skill(tmp_path, name="helper", cls="HelperSkill"):
    d = tmp_path / "skills" / name
    d.mkdir(parents=True)
    (d / "handler.py").write_text(SKILL_TEMPLATE.format(cls=cls, name=name), encoding="utf-8")
    (d / "manifest.json").write_text(
        json.dumps(
            {
                "name": name,
                "entry_point": "handler.py",
                "handler_class": cls,
                "commands": [{"trigger": "/faq"}],
            }
        ),
        encoding="utf-8",
    )


class FakeEvent:
    """Minimal stand-in for a telethon NewMessage event."""

    def __init__(self, text, chat_id=-100123, is_private=False, is_reply=False,
                 reply_sender_id=None, sender_id=42):
        self.text = text
        self.chat_id = chat_id
        self.is_private = is_private
        self.is_reply = is_reply
        self._reply_sender_id = reply_sender_id
        self._sender_id = sender_id
        self.sent: list[str] = []

    async def get_sender(self):
        return SimpleNamespace(id=self._sender_id, first_name="Тест", username="tester")

    async def get_reply_message(self):
        if not self.is_reply:
            return None
        return SimpleNamespace(sender_id=self._reply_sender_id)

    async def respond(self, text, **kwargs):
        self.sent.append(text)


@pytest.mark.asyncio
async def test_group_chatter_produces_no_reply(bot):
    """The core requirement: ordinary chatter gets no answer."""
    event = FakeEvent("привет всем, как дела?")
    await bot.handle_event(event)
    assert event.sent == []


@pytest.mark.asyncio
async def test_group_question_without_skill_content_is_silent(bot):
    """A question nobody can answer stays unanswered."""
    event = FakeEvent("Как запустить бота?")
    await bot.handle_event(event)
    assert event.sent == []


@pytest.mark.asyncio
async def test_skill_answers_question_in_group(bot, tmp_path):
    """A question the skill can answer is answered."""
    _add_skill(tmp_path)
    bot.skills.load()

    event = FakeEvent("расскажи про деплой")
    await bot.handle_event(event)
    assert event.sent == ["Деплой описан в README."]


@pytest.mark.asyncio
async def test_command_routes_to_skill(bot, tmp_path):
    _add_skill(tmp_path)
    bot.skills.load()

    event = FakeEvent("/faq оплата")
    await bot.handle_event(event)
    assert event.sent == ["FAQ: оплата"]


@pytest.mark.asyncio
async def test_command_targeting_other_bot_is_ignored(bot, tmp_path):
    _add_skill(tmp_path)
    bot.skills.load()

    event = FakeEvent("/faq@someone_else")
    await bot.handle_event(event)
    assert event.sent == []


@pytest.mark.asyncio
async def test_unknown_command_silent_in_group(bot):
    event = FakeEvent("/unknown_command")
    await bot.handle_event(event)
    assert event.sent == []


@pytest.mark.asyncio
async def test_mention_falls_back_to_personality(bot, monkeypatch, tmp_path):
    """A direct mention with no skill match still gets a personality answer."""
    called = {}

    async def fake_process(text, sender, chat_id=0):
        called["text"] = text
        return "Ответ личности"

    monkeypatch.setattr(bot, "_process_message", fake_process)

    event = FakeEvent("@my_helper_bot что нового?")
    await bot.handle_event(event)

    assert called["text"] == "что нового?"
    assert event.sent == ["Ответ личности"]


@pytest.mark.asyncio
async def test_reply_to_bot_reaches_personality(bot, monkeypatch):
    async def fake_process(text, sender, chat_id=0):
        return "уточняю"

    monkeypatch.setattr(bot, "_process_message", fake_process)

    event = FakeEvent("а подробнее?", is_reply=True, reply_sender_id=999)
    await bot.handle_event(event)
    assert event.sent == ["уточняю"]


@pytest.mark.asyncio
async def test_reply_to_other_user_is_ignored(bot, monkeypatch):
    async def fake_process(text, sender, chat_id=0):
        return "нет"

    monkeypatch.setattr(bot, "_process_message", fake_process)

    event = FakeEvent("а подробнее?", is_reply=True, reply_sender_id=1234)
    await bot.handle_event(event)
    assert event.sent == []


@pytest.mark.asyncio
async def test_private_chat_always_answered(bot, monkeypatch):
    async def fake_process(text, sender, chat_id=0):
        return "привет"

    monkeypatch.setattr(bot, "_process_message", fake_process)

    event = FakeEvent("просто болтовня", is_private=True)
    await bot.handle_event(event)
    assert event.sent == ["привет"]


@pytest.mark.asyncio
async def test_disallowed_chat_is_ignored(bot, monkeypatch, bot_module):
    """ALLOWED_CHAT_IDS restricts the bot to a specific chat."""
    monkeypatch.setattr(bot_module, "ALLOWED_CHAT_IDS", {-100999})
    asked = {}

    async def fake_process(text, sender, chat_id=0):
        asked["called"] = True
        return "x"

    monkeypatch.setattr(bot, "_process_message", fake_process)

    event = FakeEvent("@my_helper_bot привет", chat_id=-100111)
    await bot.handle_event(event)
    assert event.sent == []
    assert "called" not in asked


@pytest.mark.asyncio
async def test_allowed_chat_is_answered(bot, monkeypatch, bot_module):
    monkeypatch.setattr(bot_module, "ALLOWED_CHAT_IDS", {-100999})

    async def fake_process(text, sender, chat_id=0):
        return "работаю"

    monkeypatch.setattr(bot, "_process_message", fake_process)

    event = FakeEvent("@my_helper_bot привет", chat_id=-100999)
    await bot.handle_event(event)
    assert event.sent == ["работаю"]


@pytest.mark.asyncio
async def test_failing_skill_does_not_break_dispatch(bot, tmp_path):
    """A skill raising must not take down the message loop."""
    d = tmp_path / "skills" / "boom"
    d.mkdir(parents=True)
    (d / "handler.py").write_text(
        '''
from zero_bot_sdk import BaseSkill, SkillResponse

class BoomSkill(BaseSkill):
    name = "boom"

    async def on_command(self, ctx, command, args):
        raise RuntimeError("boom")

    async def on_message(self, ctx, text):
        raise RuntimeError("boom")
''',
        encoding="utf-8",
    )
    (d / "manifest.json").write_text(
        json.dumps({"name": "boom", "entry_point": "handler.py",
                    "handler_class": "BoomSkill",
                    "commands": [{"trigger": "/boom"}]}),
        encoding="utf-8",
    )
    bot.skills.load()

    # Command dispatch must not propagate the exception.
    event = FakeEvent("/boom")
    await bot.handle_event(event)

    # And message dispatch must not either.
    event2 = FakeEvent("@my_helper_bot тест")
    await bot.handle_event(event2)
