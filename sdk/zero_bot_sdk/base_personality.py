"""Base class for all Zero Bot personalities."""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any


class BasePersonality(ABC):
    """Personality defines how a bot communicates.

    Personalities are typically defined declaratively via manifest.json + prompt files,
    but this class allows programmatic personality logic when needed.
    """

    name: str = ""
    version: str = "0.0.0"
    system_prompt: str = ""
    greeting_template: str = ""
    fallback_template: str = ""

    def __init__(self, manifest_dir: Path | str | None = None):
        if manifest_dir:
            self._load_from_dir(Path(manifest_dir))

    def _load_from_dir(self, base: Path) -> None:
        system_path = base / "prompts" / "system.txt"
        if system_path.exists():
            self.system_prompt = system_path.read_text(encoding="utf-8").strip()

        greeting_path = base / "prompts" / "greeting.txt"
        if greeting_path.exists():
            self.greeting_template = greeting_path.read_text(encoding="utf-8").strip()

        fallback_path = base / "prompts" / "fallback.txt"
        if fallback_path.exists():
            self.fallback_template = fallback_path.read_text(encoding="utf-8").strip()

    def get_system_prompt(self, **context: Any) -> str:
        """Return the system prompt, optionally formatted with context variables."""
        return self.system_prompt.format(**context) if context else self.system_prompt

    def get_greeting(self, **context: Any) -> str:
        """Return the greeting message for a new user."""
        return self.greeting_template.format(**context) if context else self.greeting_template

    def get_fallback(self, **context: Any) -> str:
        """Return the fallback response when no skill handles the message."""
        return self.fallback_template.format(**context) if context else self.fallback_template
