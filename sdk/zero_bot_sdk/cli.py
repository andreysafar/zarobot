"""CLI tool for scaffolding skills and personalities."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click


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

GITLAB_CI_SKILL_TEMPLATE = """\
include:
  - project: 'zero-bot/zero-bot'
    ref: main
    file: '/ci/templates/skill.gitlab-ci.yml'

variables:
  SKILL_NAME: "{name}"
  SKILL_VERSION: "0.1.0"
"""

GITLAB_CI_PERSONALITY_TEMPLATE = """\
include:
  - project: 'zero-bot/zero-bot'
    ref: main
    file: '/ci/templates/personality.gitlab-ci.yml'

variables:
  PERSONALITY_NAME: "{name}"
  PERSONALITY_VERSION: "0.1.0"
"""


def _to_class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_")) + "Skill"


def _to_display_name(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


@click.group()
def main():
    """Zero Bot SDK — scaffold skills and personalities."""


@main.command()
@click.argument("entity_type", type=click.Choice(["skill", "personality"]))
@click.argument("name")
def new(entity_type: str, name: str):
    """Create a new skill or personality from template."""
    base = Path(name)
    if base.exists():
        click.echo(f"Error: directory '{name}' already exists", err=True)
        raise SystemExit(1)

    display = _to_display_name(name)

    if entity_type == "skill":
        _scaffold_skill(base, name, display)
    else:
        _scaffold_personality(base, name, display)

    click.echo(f"\n✅ {entity_type.capitalize()} '{name}' created in ./{name}/")
    click.echo(f"   cd {name} && zero-bot-sdk test")


def _scaffold_skill(base: Path, name: str, display: str):
    base.mkdir(parents=True)
    (base / "tests").mkdir()

    manifest = {**SKILL_MANIFEST_TEMPLATE, "name": name, "display_name": display}
    class_name = _to_class_name(name)
    manifest["handler_class"] = class_name
    cmd = name.split("-")[-1]

    (base / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (base / "handler.py").write_text(
        HANDLER_TEMPLATE.format(
            display_name=display, class_name=class_name, command_name=cmd,
        )
    )
    (base / "tests" / "test_handler.py").write_text(
        TEST_HANDLER_TEMPLATE.format(display_name=display, command_name=cmd)
    )
    (base / "requirements.txt").write_text("zero-bot-sdk>=0.1.0\n")
    (base / ".gitlab-ci.yml").write_text(GITLAB_CI_SKILL_TEMPLATE.format(name=name))
    (base / "README.md").write_text(f"# {display}\n\nA Zero Bot skill.\n")


def _scaffold_personality(base: Path, name: str, display: str):
    base.mkdir(parents=True)
    (base / "prompts").mkdir()
    (base / "training").mkdir()
    (base / "tests").mkdir()

    manifest = {**PERSONALITY_MANIFEST_TEMPLATE, "name": name, "display_name": display}
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    (base / "prompts" / "system.txt").write_text(
        f"You are {display}, an AI assistant.\n\nDescribe your personality here.\n"
    )
    (base / "prompts" / "greeting.txt").write_text(
        "Привет, {user_name}! 👋\n\nЯ {bot_name}. Чем могу помочь?\n"
    )
    (base / "prompts" / "fallback.txt").write_text(
        "Я не совсем понял. Попробуйте переформулировать или используйте /help.\n"
    )
    (base / "training" / "examples.jsonl").write_text(
        '{"user": "Привет!", "bot": "Привет! Рад знакомству!"}\n'
    )
    (base / "training" / "style_guide.md").write_text(
        f"# {display} — Style Guide\n\nDescribe the writing style here.\n"
    )
    (base / "tests" / "test_personality.py").write_text(
        f'"""Tests for {display} personality."""\n\n'
        "from zero_bot_sdk.testing import PersonalityTestHarness\n\n\n"
        "def test_system_prompt():\n"
        '    h = PersonalityTestHarness(".")\n'
        "    assert h.test_system_prompt_exists()\n\n\n"
        "def test_greeting():\n"
        '    h = PersonalityTestHarness(".")\n'
        "    assert h.test_greeting_exists()\n"
    )
    (base / "requirements.txt").write_text("zero-bot-sdk>=0.1.0\n")
    (base / ".gitlab-ci.yml").write_text(GITLAB_CI_PERSONALITY_TEMPLATE.format(name=name))
    (base / "README.md").write_text(f"# {display}\n\nA Zero Bot personality.\n")


@main.command()
def test():
    """Run tests for the current skill or personality."""
    cwd = Path.cwd()
    manifest = cwd / "manifest.json"
    if not manifest.exists():
        click.echo("Error: manifest.json not found. Are you in a skill/personality directory?", err=True)
        raise SystemExit(1)

    os.system("python -m pytest tests/ -v")


@main.command()
def chat():
    """Interactive chat mode for testing skills."""
    click.echo("Interactive chat mode — coming soon!")


if __name__ == "__main__":
    main()
