"""Templates for zero-bot-sdk scaffold (skills and personalities)."""

SKILL_MANIFEST_TEMPLATE = {
    "schema_version": "1.0",
    "name": "",
    "display_name": "",
    "description": "A new Zero Bot skill",
    "version": "0.1.0",
    "author": {"name": "", "github": "", "solana_address": ""},
    "category": "utilities",
    "tags": [],
    "icon": "icon.png",
    "entry_point": "handler.py",
    "handler_class": "",
    "commands": [{"trigger": "/example", "description": "Example command", "usage": "/example args"}],
    "message_patterns": [],
    "config_schema": {},
    "requirements": [],
    "pricing": {
        "price_ia_coins": 0,
        "is_free": True,
        "revenue_share": {"creator": 0.60, "platform": 0.30, "telegram": 0.10},
    },
    "compatibility": {"min_bot_level": 0, "max_skills_conflict": [], "required_skills": []},
    "solana": {"registry_address": None, "tx_hash": None},
}

PERSONALITY_MANIFEST_TEMPLATE = {
    "schema_version": "1.0",
    "name": "",
    "display_name": "",
    "description": "A new Zero Bot personality",
    "version": "0.1.0",
    "author": {"name": "", "github": "", "solana_address": ""},
    "category": "general",
    "tags": [],
    "language": "ru",
    "avatar": "avatar.png",
    "banner": "banner.png",
    "prompts": {
        "system": "prompts/system.txt",
        "greeting": "prompts/greeting.txt",
        "fallback": "prompts/fallback.txt",
    },
    "training": {"examples": "training/examples.jsonl", "style_guide": "training/style_guide.md"},
    "ai_model": {"preferred": "claude-sonnet-4-20250514", "fallback": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1024},
    "behavior": {"response_style": "balanced", "emoji_usage": "moderate", "formality": "medium", "humor_level": "medium"},
    "pricing": {
        "price_ia_coins": 0,
        "is_free": True,
        "revenue_share": {"creator": 0.60, "platform": 0.30, "telegram": 0.10},
    },
    "compatibility": {"min_bot_level": 0, "conflicts_with": []},
    "solana": {"registry_address": None, "tx_hash": None},
}

HANDLER_TEMPLATE = '''\
"""
Skill: {display_name}
"""

from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse


class {class_name}(BaseSkill):
    """TODO: Describe your skill."""

    async def on_install(self, ctx: SkillContext) -> None:
        pass

    async def on_command(self, ctx: SkillContext, command: str, args: str) -> SkillResponse:
        if command == "/{command_name}":
            return SkillResponse(text=f"Hello from {display_name}! Args: {{args}}")
        return SkillResponse.skip()

    async def on_message(self, ctx: SkillContext, text: str) -> SkillResponse:
        return SkillResponse.skip()

    async def on_uninstall(self, ctx: SkillContext) -> None:
        pass
'''

TEST_HANDLER_TEMPLATE = '''\
"""Tests for {display_name} skill."""

import pytest
from zero_bot_sdk.testing import SkillTestHarness


@pytest.fixture
def harness():
    return SkillTestHarness("handler.py")


@pytest.mark.asyncio
async def test_command(harness):
    response = await harness.send_command("/{command_name}", "test")
    assert response.has_content()


@pytest.mark.asyncio
async def test_skip_unrelated(harness):
    response = await harness.send_message("random message")
    assert response.is_skip()
'''

GITLAB_CI_SKILL = """\
include:
  - project: 'zero-bot/zero-bot'
    ref: main
    file: '/ci/templates/skill.gitlab-ci.yml'

variables:
  SKILL_NAME: "{name}"
  SKILL_VERSION: "0.1.0"
"""

GITLAB_CI_PERSONALITY = """\
include:
  - project: 'zero-bot/zero-bot'
    ref: main
    file: '/ci/templates/personality.gitlab-ci.yml'

variables:
  PERSONALITY_NAME: "{name}"
  PERSONALITY_VERSION: "0.1.0"
"""

PERSONALITY_TEST_TEMPLATE = '''\
"""Tests for {display} personality."""

from zero_bot_sdk.testing import PersonalityTestHarness


def test_system_prompt():
    h = PersonalityTestHarness(".")
    assert h.test_system_prompt_exists()


def test_greeting():
    h = PersonalityTestHarness(".")
    assert h.test_greeting_exists()
'''
