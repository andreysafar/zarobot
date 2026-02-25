"""CLI tool for scaffolding skills and personalities."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from .cli_templates import (
    GITLAB_CI_PERSONALITY,
    GITLAB_CI_SKILL,
    HANDLER_TEMPLATE,
    PERSONALITY_MANIFEST_TEMPLATE,
    PERSONALITY_TEST_TEMPLATE,
    SKILL_MANIFEST_TEMPLATE,
    TEST_HANDLER_TEMPLATE,
)


def _to_class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_")) + "Skill"


def _to_display_name(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


def _scaffold_skill(base: Path, name: str, display: str) -> None:
    base.mkdir(parents=True)
    (base / "tests").mkdir()
    manifest = {**SKILL_MANIFEST_TEMPLATE, "name": name, "display_name": display}
    class_name = _to_class_name(name)
    manifest["handler_class"] = class_name
    cmd = name.split("-")[-1]
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (base / "handler.py").write_text(
        HANDLER_TEMPLATE.format(display_name=display, class_name=class_name, command_name=cmd)
    )
    (base / "tests" / "test_handler.py").write_text(
        TEST_HANDLER_TEMPLATE.format(display_name=display, command_name=cmd)
    )
    (base / "requirements.txt").write_text("zero-bot-sdk>=0.1.0\n")
    (base / ".gitlab-ci.yml").write_text(GITLAB_CI_SKILL.format(name=name))
    (base / "README.md").write_text(f"# {display}\n\nA Zero Bot skill.\n")


def _scaffold_personality(base: Path, name: str, display: str) -> None:
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
    (base / "training" / "examples.jsonl").write_text('{"user": "Привет!", "bot": "Привет! Рад знакомству!"}\n')
    (base / "training" / "style_guide.md").write_text(f"# {display} — Style Guide\n\nDescribe the writing style here.\n")
    (base / "tests" / "test_personality.py").write_text(PERSONALITY_TEST_TEMPLATE.format(display=display))
    (base / "requirements.txt").write_text("zero-bot-sdk>=0.1.0\n")
    (base / ".gitlab-ci.yml").write_text(GITLAB_CI_PERSONALITY.format(name=name))
    (base / "README.md").write_text(f"# {display}\n\nA Zero Bot personality.\n")


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


@main.command()
def test():
    """Run tests for the current skill or personality."""
    manifest = Path.cwd() / "manifest.json"
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
