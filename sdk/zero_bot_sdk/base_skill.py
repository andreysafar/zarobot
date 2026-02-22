"""Base class for all Zero Bot skills."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .context import SkillContext
from .response import SkillResponse


class BaseSkill(ABC):
    """Every skill MUST inherit from BaseSkill and implement the required methods.

    Lifecycle:
        on_install   → Called once when the skill is installed on a bot
        on_command   → Called when user sends a registered /command
        on_message   → Called for every non-command message
        on_callback  → Called for inline button presses
        on_event     → Called for system events
        on_uninstall → Called when the skill is removed from a bot
    """

    name: str = ""
    version: str = "0.0.0"

    async def on_install(self, ctx: SkillContext) -> None:
        """Called once when the skill is installed. Override to initialize resources."""

    @abstractmethod
    async def on_command(self, ctx: SkillContext, command: str, args: str) -> SkillResponse:
        """Handle a /command. Return SkillResponse.skip() if not handling this command."""
        ...

    async def on_message(self, ctx: SkillContext, text: str) -> SkillResponse:
        """Handle a plain text message. Default: skip to next skill."""
        return SkillResponse.skip()

    async def on_callback(self, ctx: SkillContext, data: str) -> SkillResponse:
        """Handle an inline button callback. Default: skip."""
        return SkillResponse.skip()

    async def on_event(self, ctx: SkillContext, event_type: str, payload: dict) -> None:
        """Handle system events (level_up, new_user, daily_reset, etc.)."""

    async def on_uninstall(self, ctx: SkillContext) -> None:
        """Cleanup when the skill is removed from a bot."""
