"""Skill and personality response objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResponse:
    """Response returned by a skill handler.

    text: message text to send
    buttons: inline keyboard rows [[("label", "callback_data"), ...], ...]
    image_url: URL of image to send
    _skip: if True, this skill passes the message to the next skill in chain
    _consume: if True, stops the skill chain (no further skills or personality)
    """

    text: str | None = None
    buttons: list[list[tuple[str, str]]] | None = None
    image_url: str | None = None
    file_path: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    _skip: bool = False
    _consume: bool = False

    @classmethod
    def skip(cls) -> "SkillResponse":
        """Pass this message to the next skill in the chain."""
        return cls(_skip=True)

    @classmethod
    def consume(cls) -> "SkillResponse":
        """Stop the skill chain — no further skills or personality will handle this message."""
        return cls(_consume=True)

    def is_skip(self) -> bool:
        return self._skip

    def is_consume(self) -> bool:
        return self._consume

    def has_content(self) -> bool:
        return bool(self.text or self.image_url or self.file_path)
