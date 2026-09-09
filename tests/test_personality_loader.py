"""Tests for personality path resolution.

The Docker image ships all personalities under /data/personality/<id>/, while
some deployments flatten one personality into /data/personality/ directly.
Both must resolve.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

BOT_MODULE = Path(__file__).resolve().parent.parent / "services" / "bot-instance" / "bot.py"


@pytest.fixture(scope="module")
def bot_module():
    spec = importlib.util.spec_from_file_location("bot_instance_under_test", BOT_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot_instance_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _write_personality(root: Path, name: str = "Ия", activation: str = "ия"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "name": "ia",
                "display_name": name,
                "prompts": {"system": "prompts/system.txt", "fallback": "prompts/fallback.txt"},
                "behavior": {"activation_phrase": activation},
            }
        ),
        encoding="utf-8",
    )
    prompts = root / "prompts"
    prompts.mkdir(exist_ok=True)
    (prompts / "system.txt").write_text("Ты — Ия.", encoding="utf-8")
    (prompts / "fallback.txt").write_text("Не поняла.", encoding="utf-8")


def test_nested_layout_resolves_by_id(bot_module, tmp_path):
    """Image layout: /data/personality/ia/manifest.json"""
    _write_personality(tmp_path / "ia")
    loader = bot_module.PersonalityLoader(tmp_path, "ia")

    assert loader.dir == tmp_path / "ia"
    assert loader.system_prompt == "Ты — Ия."
    assert loader.fallback == "Не поняла."
    assert loader.activation_phrase == "ия"


def test_flattened_layout_falls_back_to_root(bot_module, tmp_path):
    """Flattened layout: /data/personality/manifest.json"""
    _write_personality(tmp_path)
    loader = bot_module.PersonalityLoader(tmp_path, "ia")

    assert loader.dir == tmp_path
    assert loader.system_prompt == "Ты — Ия."


def test_missing_manifest_uses_defaults(bot_module, tmp_path):
    loader = bot_module.PersonalityLoader(tmp_path, "ia")

    assert "helpful" in loader.system_prompt
    assert loader.fallback
    assert loader.activation_phrase is None


def test_auxiliary_prompt_lookup(bot_module, tmp_path):
    root = tmp_path / "ia"
    _write_personality(root)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "display_name": "Ия",
                "prompts": {"summary_agent": "prompts/summary_agent.txt"},
                "behavior": {},
            }
        ),
        encoding="utf-8",
    )
    (root / "prompts" / "summary_agent.txt").write_text("Суммаризируй.", encoding="utf-8")

    loader = bot_module.PersonalityLoader(tmp_path, "ia")
    assert loader.prompt("summary_agent") == "Суммаризируй."
    assert loader.prompt("does_not_exist") == ""
