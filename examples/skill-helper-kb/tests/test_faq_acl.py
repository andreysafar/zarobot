"""
Права на управление FAQ.

Проверяем то, чего не проверяла демка: она подставляла OWNER_ID и обходила
реальную проверку админа, так что is_chat_admin не выполнялся ни разу.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from telethon.tl.types import (
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
    ChannelParticipantSelf,
)
from zero_bot_sdk import SkillContext

SKILL_DIR = Path(__file__).resolve().parents[1]


def _load_handler():
    spec = importlib.util.spec_from_file_location(
        "helper_kb_handler_test", SKILL_DIR / "handler.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


handler_mod = _load_handler()
perms = handler_mod._perms
HelperKbSkill = handler_mod.HelperKbSkill

CHAT = -1001234567890
ADMIN = 111
STRANGER = 222
OWNER = 999


def participant(cls):
    """Собрать TL-объект без __init__: для isinstance большего не нужно."""
    return object.__new__(cls)


class FakeClient:
    """Клиент Telethon: отвечает на GetParticipantRequest заданным типом."""

    def __init__(self, participant_type=None, raises=None):
        self.participant_type = participant_type
        self.raises = raises
        self.calls = 0

    async def __call__(self, request):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        inner = participant(self.participant_type)
        return type("Result", (), {"participant": inner})()


@pytest.fixture
def store(tmp_path):
    from dervaler.store import Store

    s = Store(tmp_path / "kb.sqlite3")
    yield s
    s.close()


@pytest.fixture(autouse=True)
def no_owner(monkeypatch):
    """По умолчанию владельца нет — иначе проверка админа не выполняется."""
    monkeypatch.setattr(perms, "OWNER_IDS", set())


def ctx(user_id, is_private=False):
    return SkillContext(
        bot_id="test", user_id=user_id, chat_id=CHAT,
        config={"is_private": is_private},
    )


def make_skill(store, client):
    return HelperKbSkill(store=store, telegram_client=client)


ADMIN_COMMANDS = ["/faq_add", "/faq_edit", "/faq_del", "/faq_publish"]


@pytest.mark.parametrize("command", ADMIN_COMMANDS)
async def test_stranger_cannot_touch_faq(store, command):
    """Обычный участник не редактирует FAQ ни одной из команд."""
    skill = make_skill(store, FakeClient(ChannelParticipantSelf))

    resp = await skill.on_command(ctx(STRANGER), command, "вопрос | ответ")

    assert "только для администраторов" in resp.text
    assert store.list_faq(CHAT, status=None) == []


@pytest.mark.parametrize("kind", [ChannelParticipantAdmin, ChannelParticipantCreator])
async def test_admin_and_creator_can_add(store, kind):
    skill = make_skill(store, FakeClient(kind))

    resp = await skill.on_command(ctx(ADMIN), "/faq_add", "Как деплоить? | docker compose up")

    assert "Черновик" in resp.text
    assert len(store.list_faq(CHAT, status=None)) == 1


async def test_owner_is_admin_without_telegram_call(store, monkeypatch):
    """OWNER_ID работает даже когда клиента нет (личка, локальный запуск)."""
    monkeypatch.setattr(perms, "OWNER_IDS", {OWNER})
    client = FakeClient(ChannelParticipantSelf)
    skill = make_skill(store, client)

    resp = await skill.on_command(ctx(OWNER), "/faq_add", "Вопрос? | Ответ")

    assert "Черновик" in resp.text
    assert client.calls == 0  # до Telegram дело не дошло


async def test_private_chat_denies_non_owner(store):
    """В личке правами админа группы не пользуются — только владелец."""
    skill = make_skill(store, FakeClient(ChannelParticipantAdmin))

    resp = await skill.on_command(ctx(ADMIN, is_private=True), "/faq_add", "В? | О")

    assert "только для администраторов" in resp.text


async def test_rpc_error_denies_access(store):
    """Если Telegram не ответил — прав нет. Fail closed, а не открыто."""
    from telethon.errors import RPCError

    skill = make_skill(store, FakeClient(raises=RPCError(request=None, message="boom")))

    resp = await skill.on_command(ctx(ADMIN), "/faq_del", "1")

    assert "только для администраторов" in resp.text


async def test_no_client_denies_access(store):
    """Без клиента проверить админа нельзя — значит отказ."""
    skill = make_skill(store, None)

    resp = await skill.on_command(ctx(ADMIN), "/faq_publish", "1")

    assert "только для администраторов" in resp.text
