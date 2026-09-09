"""
Тесты личности Дервалера.

Главное: Дервалер — это НЕ Ия и не публичный хелпер. Проверяем, что манифест
загружается существующим загрузчиком и явно помечен как воркер, который
не отвечает в публичном чате.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BOT_MODULE = ROOT / "services" / "bot-instance" / "bot.py"
PERSONALITY_DIR = ROOT / "personalities" / "dervaler"


@pytest.fixture(scope="module")
def bot_module():
    spec = importlib.util.spec_from_file_location("bot_for_dervaler", BOT_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bot_for_dervaler"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def manifest():
    return json.loads((PERSONALITY_DIR / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def loader(bot_module, tmp_path_factory):
    root = tmp_path_factory.mktemp("personalities")
    (root / "dervaler").symlink_to(PERSONALITY_DIR)
    return bot_module.PersonalityLoader(root, "dervaler")


def test_personality_files_exist():
    assert (PERSONALITY_DIR / "manifest.json").is_file()
    assert (PERSONALITY_DIR / "prompts" / "system.txt").is_file()
    assert (PERSONALITY_DIR / "prompts" / "summary_agent.txt").is_file()
    assert (PERSONALITY_DIR / "prompts" / "fallback.txt").is_file()


def test_manifest_is_marked_as_worker(manifest):
    assert manifest["name"] == "dervaler"
    assert manifest.get("is_worker") is True
    assert manifest.get("is_default") is False


def test_identity_is_user_session_not_bot(manifest):
    """Дервалер входит пользователем, а не бот-токеном."""
    identity = manifest["identity"]
    assert identity["telegram_kind"] == "user"
    assert identity["client"] == "telethon"


def test_must_not_speak_in_public_chat(manifest):
    assert manifest["behavior"]["speaks_in_public_chat"] is False
    assert manifest["features"]["public_replies"] is False


def test_prompts_load(loader):
    assert loader.system_prompt
    assert loader.fallback
    assert loader.prompt("summary_agent")
    assert loader.display_name == "Дервалер"


def test_system_prompt_states_restrictions(loader):
    """Промпт явно запрещает писать в публичный чат."""
    text = loader.system_prompt.lower()
    assert "не пиши в публичный чат" in text
    assert "архивариус" in text


def test_not_reusing_ia_prompts(loader, bot_module, tmp_path_factory):
    """Дервалер не должен тащить промпты Ии."""
    root = tmp_path_factory.mktemp("both")
    (root / "dervaler").symlink_to(PERSONALITY_DIR)
    (root / "ia").symlink_to(ROOT / "personalities" / "ia")

    dervaler = bot_module.PersonalityLoader(root, "dervaler")
    ia = bot_module.PersonalityLoader(root, "ia")

    assert dervaler.system_prompt != ia.system_prompt
    assert dervaler.dir == root / "dervaler"
    assert ia.dir == root / "ia"


def test_activation_phrase_present(manifest):
    assert manifest["behavior"]["activation_phrase"] == "дервалер"
