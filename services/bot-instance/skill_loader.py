"""
Skill loader for Zero Bot instances.

Scans /data/skills for skill packages and instantiates them.

Expected layout for each skill directory:

    /data/skills/<skill-name>/
        manifest.json   — {"name", "entry_point": "handler.py",
                           "handler_class": "MySkill", "commands": [...]}
        handler.py      — defines a BaseSkill subclass

The manifest is optional: if it is missing, the loader falls back to
`handler.py` and auto-detects the first BaseSkill subclass in the module.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from zero_bot_sdk import BaseSkill


@dataclass
class LoadedSkill:
    """A skill instance plus its manifest metadata."""

    name: str
    instance: BaseSkill
    commands: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    directory: Path | None = None


def _import_module(module_name: str, path: Path):
    """Import a Python module from an explicit file path.

    The module is executed under a throwaway name: keeping it out of a stable
    sys.modules slot means a reload picks up edited files instead of reusing
    a cached module object.
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses / postponed annotations resolve.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    finally:
        # Drop the temporary entry so a later load re-executes the file.
        sys.modules.pop(module_name, None)
    return module


def _find_skill_class(module, class_name: str | None = None) -> type[BaseSkill]:
    """Locate the BaseSkill subclass inside an imported module."""
    if class_name:
        cls = getattr(module, class_name, None)
        if cls is None or not (inspect.isclass(cls) and issubclass(cls, BaseSkill)):
            raise ImportError(f"Handler class '{class_name}' not a BaseSkill subclass")
        return cls

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseSkill) and obj is not BaseSkill:
            # Skip classes merely imported from the SDK.
            if obj.__module__ == module.__name__:
                return obj
    raise ImportError(f"No BaseSkill subclass found in {module.__name__}")


def load_skill(directory: Path) -> LoadedSkill | None:
    """Load a single skill from its directory. Returns None on failure."""
    manifest: dict[str, Any] = {}
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error("Bad manifest for skill {}: {}", directory.name, e)
            return None
    elif directory.suffix == ".json":
        # Loose manifest file without a directory — not a skill package.
        return None

    entry_point = manifest.get("entry_point", "handler.py")
    handler_path = directory / entry_point
    if not handler_path.exists():
        logger.warning("Skill {} has no {} — skipped", directory.name, entry_point)
        return None

    module_name = f"zero_skill_{directory.name.replace('-', '_')}"
    try:
        module = _import_module(module_name, handler_path)
        skill_cls = _find_skill_class(module, manifest.get("handler_class"))
        instance = skill_cls()
    except Exception as e:
        logger.error("Failed to load skill {}: {}", directory.name, e)
        return None

    commands = [c["trigger"] for c in manifest.get("commands", []) if "trigger" in c]
    # Fall back to the class-level declaration if the manifest omits commands.
    commands = commands or list(getattr(instance, "commands", []) or [])

    return LoadedSkill(
        name=manifest.get("name") or getattr(instance, "name", "") or directory.name,
        instance=instance,
        commands=commands,
        config=manifest.get("config", {}),
        directory=directory,
    )


class SkillManager:
    """Loads skills from a directory and dispatches messages through them."""

    def __init__(self, skills_dir: Path):
        self.dir = skills_dir
        self.skills: list[LoadedSkill] = []
        self._by_command: dict[str, LoadedSkill] = {}

    def load(self) -> list[LoadedSkill]:
        """Scan the skills directory and instantiate every valid skill."""
        self.skills = []
        self._by_command = {}

        if not self.dir.exists():
            logger.info("No skills directory at {} — running without skills", self.dir)
            return self.skills

        for entry in sorted(self.dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith((".", "_")):
                continue
            skill = load_skill(entry)
            if skill is None:
                continue
            for command in skill.commands:
                # Normalize "/weather@MyBot" and "/weather" to the same key.
                self._by_command[command.split("@")[0].lower()] = skill
            self.skills.append(skill)
            logger.info("Loaded skill {} v{} ({})", skill.name,
                        getattr(skill.instance, "version", "?"), entry.name)

        return self.skills

    def get_skill_for_command(self, command: str) -> LoadedSkill | None:
        """Return the skill registered for a command, if any."""
        return self._by_command.get(command.split("@")[0].lower())

    @property
    def command_names(self) -> list[str]:
        return sorted(self._by_command)

    async def install_all(self, ctx) -> None:
        """Call on_install for every skill, isolating failures."""
        for skill in self.skills:
            try:
                await skill.instance.on_install(ctx)
            except Exception as e:
                logger.error("on_install failed for skill {}: {}", skill.name, e)

    async def uninstall_all(self, ctx) -> None:
        """Call on_uninstall for every skill, isolating failures."""
        for skill in self.skills:
            try:
                await skill.instance.on_uninstall(ctx)
            except Exception as e:
                logger.error("on_uninstall failed for skill {}: {}", skill.name, e)
