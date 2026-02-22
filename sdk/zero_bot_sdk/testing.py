"""Test harnesses for skills and personalities."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .base_skill import BaseSkill
from .context import SkillContext
from .response import SkillResponse


class SkillTestHarness:
    """Test harness that loads a skill and simulates messages.

    Usage:
        harness = SkillTestHarness("handler.py", config={"api_key": "test"})
        response = await harness.send_command("/weather", "Moscow")
        assert response.text is not None
    """

    def __init__(self, handler_path: str, config: dict | None = None, **ctx_overrides):
        self.skill = self._load_skill(handler_path)
        self.config = config or {}
        self.ctx_overrides = ctx_overrides
        self._installed = False

    def _load_skill(self, path: str) -> BaseSkill:
        spec = importlib.util.spec_from_file_location("skill_module", path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load skill from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["skill_module"] = module
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseSkill)
                and attr is not BaseSkill
            ):
                return attr()
        raise ValueError(f"No BaseSkill subclass found in {path}")

    def _make_ctx(self) -> SkillContext:
        return SkillContext.for_testing(config=self.config, **self.ctx_overrides)

    async def _ensure_installed(self) -> None:
        if not self._installed:
            await self.skill.on_install(self._make_ctx())
            self._installed = True

    async def send_command(self, command: str, args: str = "") -> SkillResponse:
        await self._ensure_installed()
        return await self.skill.on_command(self._make_ctx(), command, args)

    async def send_message(self, text: str) -> SkillResponse:
        await self._ensure_installed()
        return await self.skill.on_message(self._make_ctx(), text)

    async def send_callback(self, data: str) -> SkillResponse:
        await self._ensure_installed()
        return await self.skill.on_callback(self._make_ctx(), data)


class PersonalityTestHarness:
    """Test harness for personality prompt validation."""

    def __init__(self, personality_dir: str):
        from .base_personality import BasePersonality
        self.personality = BasePersonality(manifest_dir=personality_dir)

    def test_system_prompt_exists(self) -> bool:
        return len(self.personality.system_prompt) > 0

    def test_greeting_exists(self) -> bool:
        return len(self.personality.greeting_template) > 0

    def test_greeting_renders(self, **context) -> str:
        return self.personality.get_greeting(**context)
