"""Tests for the skill loader — skills in /data/skills must actually load."""

import json

import pytest

from skill_loader import LoadedSkill, SkillManager, load_skill
from zero_bot_sdk import SkillContext

HANDLER_TEMPLATE = '''
from zero_bot_sdk import BaseSkill, SkillResponse

class {cls}(BaseSkill):
    name = "{name}"
    version = "1.0.0"

    async def on_command(self, ctx, command, args):
        if command == "/ping":
            return SkillResponse(text="pong")
        return SkillResponse.skip()
'''


def _make_skill(tmp_path, dir_name, cls="DemoSkill", name="demo", manifest=True):
    d = tmp_path / dir_name
    d.mkdir()
    (d / "handler.py").write_text(
        HANDLER_TEMPLATE.format(cls=cls, name=name), encoding="utf-8"
    )
    if manifest:
        (d / "manifest.json").write_text(
            json.dumps(
                {
                    "name": name,
                    "entry_point": "handler.py",
                    "handler_class": cls,
                    "commands": [{"trigger": "/ping"}],
                    "config": {"units": "metric"},
                }
            ),
            encoding="utf-8",
        )
    return d


def test_load_skill_with_manifest(tmp_path):
    d = _make_skill(tmp_path, "demo")
    skill = load_skill(d)

    assert isinstance(skill, LoadedSkill)
    assert skill.name == "demo"
    assert skill.commands == ["/ping"]
    assert skill.config == {"units": "metric"}


def test_load_skill_autodetects_class_without_manifest(tmp_path):
    d = _make_skill(tmp_path, "auto", cls="AutoSkill", name="auto", manifest=False)
    skill = load_skill(d)

    assert skill is not None
    assert skill.instance.name == "auto"
    # No manifest means no declared commands.
    assert skill.commands == []


def test_load_skill_missing_handler_is_skipped(tmp_path):
    d = tmp_path / "broken"
    d.mkdir()
    (d / "manifest.json").write_text('{"name": "broken"}', encoding="utf-8")
    assert load_skill(d) is None


def test_load_skill_with_syntax_error_is_skipped(tmp_path):
    d = tmp_path / "bad"
    d.mkdir()
    (d / "handler.py").write_text("def oops(:\n", encoding="utf-8")
    (d / "manifest.json").write_text('{"name": "bad"}', encoding="utf-8")
    assert load_skill(d) is None


def test_manager_loads_all_skills(tmp_path):
    _make_skill(tmp_path, "alpha", cls="AlphaSkill", name="alpha")
    _make_skill(tmp_path, "beta", cls="BetaSkill", name="beta")
    (tmp_path / "notes.txt").write_text("not a skill", encoding="utf-8")
    (tmp_path / ".hidden").mkdir()

    manager = SkillManager(tmp_path)
    loaded = manager.load()

    assert {s.name for s in loaded} == {"alpha", "beta"}
    assert manager.command_names == ["/ping"]


def test_manager_missing_dir_is_empty(tmp_path):
    manager = SkillManager(tmp_path / "nope")
    assert manager.load() == []
    assert manager.command_names == []


def test_command_lookup_normalizes_bot_suffix(tmp_path):
    _make_skill(tmp_path, "demo")
    manager = SkillManager(tmp_path)
    manager.load()

    assert manager.get_skill_for_command("/ping") is not None
    assert manager.get_skill_for_command("/ping@MyBot") is not None
    assert manager.get_skill_for_command("/PING") is not None
    assert manager.get_skill_for_command("/unknown") is None


@pytest.mark.asyncio
async def test_skill_command_dispatch(tmp_path):
    _make_skill(tmp_path, "demo")
    manager = SkillManager(tmp_path)
    manager.load()

    skill = manager.get_skill_for_command("/ping")
    ctx = SkillContext.for_testing()
    response = await skill.instance.on_command(ctx, "/ping", "")

    assert response.text == "pong"
    assert not response.is_skip()


@pytest.mark.asyncio
async def test_install_all_isolates_failures(tmp_path):
    d = _make_skill(tmp_path, "demo")
    (d / "handler.py").write_text(
        '''
from zero_bot_sdk import BaseSkill

class BoomSkill(BaseSkill):
    name = "boom"

    async def on_install(self, ctx):
        raise RuntimeError("boom")

    async def on_command(self, ctx, command, args):
        return None
''',
        encoding="utf-8",
    )
    (d / "manifest.json").write_text(
        json.dumps({"name": "boom", "entry_point": "handler.py",
                    "handler_class": "BoomSkill", "commands": []}),
        encoding="utf-8",
    )

    manager = SkillManager(tmp_path)
    manager.load()
    # Must not raise even though on_install fails.
    await manager.install_all(SkillContext.for_testing())
