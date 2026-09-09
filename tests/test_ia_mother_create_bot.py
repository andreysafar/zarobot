"""
Мастер создания бота: токен от BotFather → паспорт → контейнер.

Раньше поток обрывался после первого шага: колбэк create_bot спрашивал имя,
а обработчика текстовых сообщений не было вообще, поэтому шаги 2 и 3 не
выполнялись никогда — ни паспорта, ни контейнера не появлялось.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

import config

ROOT = Path(__file__).resolve().parents[1]


def _load_my_bots():
    """
    Загрузить обработчик по пути.

    Просто `from handlers import my_bots` не годится: пакет `handlers` есть и
    у ia-mother, и у bot-instance, и в sys.path первым стоит второй.
    """
    path = ROOT / "services" / "ia-mother" / "handlers" / "my_bots.py"
    spec = importlib.util.spec_from_file_location("ia_mother_my_bots", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


my_bots = _load_my_bots()
OWNER = 555
STRANGER = 999


class FakeEvent:
    """Событие Telethon: запоминает, что бот ответил."""

    def __init__(self, text="", sender_id=OWNER, username="owner"):
        self.text = text
        self.is_private = True
        self._sender = types.SimpleNamespace(id=sender_id, username=username)
        self.replies: list[str] = []

    async def get_sender(self):
        return self._sender

    async def edit(self, text, **kw):
        self.replies.append(text)

    async def respond(self, text, **kw):
        self.replies.append(text)


class FakeAPI:
    """Core API: отдаёт паспорт и запоминает привязку контейнера."""

    def __init__(self):
        self.container_updates = []

    async def create_passport(self, owner_id, owner_telegram, name):
        self.created = {"owner_id": owner_id, "name": name}
        return {"id": "bot-42"}

    async def update_bot_container(self, bot_id, container_id):
        self.container_updates.append((bot_id, container_id))


class FakeBot:
    def __init__(self):
        self.api = FakeAPI()


@pytest.fixture
def spawned(monkeypatch):
    """Подменяем docker: контейнеры в тестах не поднимаем."""
    calls = []

    class FakeManager:
        async def spawn_bot(self, **kwargs):
            calls.append(kwargs)
            return {"success": True, "container_id": "c" * 20}

    module = types.ModuleType("docker_manager")
    module.BotContainerManager = FakeManager
    monkeypatch.setitem(sys.modules, "docker_manager", module)
    return calls


@pytest.fixture(autouse=True)
def owner_only(monkeypatch):
    """По умолчанию создавать ботов может только владелец."""
    monkeypatch.setattr(config, "OWNER_ID", OWNER)
    monkeypatch.setattr(config, "ALLOWED_CREATOR_IDS", set())
    monkeypatch.setattr(config, "ALLOW_PUBLIC_BOT_CREATION", False)


async def test_full_wizard_creates_passport_and_container(spawned):
    bot = FakeBot()

    step1 = FakeEvent()
    await my_bots.handle_create_bot(step1, bot)
    assert my_bots.get_create_state(bot, OWNER)["step"] == 1

    step2 = FakeEvent("МойПомощник")
    await my_bots.handle_create_bot_name(step2, bot)
    assert my_bots.get_create_state(bot, OWNER)["step"] == 2

    step3 = FakeEvent("123456789:AAExampleTokenFromBotFather")
    await my_bots.handle_create_bot_token(step3, bot)

    assert bot.api.created == {"owner_id": OWNER, "name": "МойПомощник"}
    assert spawned[0]["bot_token"] == "123456789:AAExampleTokenFromBotFather"
    assert spawned[0]["bot_name"] == "МойПомощник"
    assert bot.api.container_updates == [("bot-42", "c" * 20)]
    # Состояние очищено — мастер не залипает.
    assert my_bots.get_create_state(bot, OWNER) is None


async def test_stranger_cannot_spawn_containers(spawned):
    bot = FakeBot()
    event = FakeEvent(sender_id=STRANGER)

    await my_bots.handle_create_bot(event, bot)

    assert "ограничено" in event.replies[0]
    assert my_bots.get_create_state(bot, STRANGER) is None
    assert spawned == []


async def test_two_users_do_not_share_state(spawned):
    """Состояние на пользователя: чужой токен не должен утекать в чужого бота."""
    import config as cfg
    cfg.ALLOWED_CREATOR_IDS = {OWNER, STRANGER}
    bot = FakeBot()

    await my_bots.handle_create_bot(FakeEvent(sender_id=OWNER), bot)
    await my_bots.handle_create_bot(FakeEvent(sender_id=STRANGER, username="other"), bot)

    await my_bots.handle_create_bot_name(FakeEvent("БотАнны", sender_id=OWNER), bot)
    await my_bots.handle_create_bot_name(FakeEvent("БотПети", sender_id=STRANGER), bot)

    assert my_bots.get_create_state(bot, OWNER)["bot_name"] == "БотАнны"
    assert my_bots.get_create_state(bot, STRANGER)["bot_name"] == "БотПети"


async def test_invalid_token_is_rejected(spawned):
    bot = FakeBot()
    await my_bots.handle_create_bot(FakeEvent(), bot)
    await my_bots.handle_create_bot_name(FakeEvent("Бот"), bot)

    event = FakeEvent("не-токен")
    await my_bots.handle_create_bot_token(event, bot)

    assert "Неверный формат токена" in event.replies[0]
    assert spawned == []


def test_wizard_steps_are_wired_to_an_event_handler():
    """
    Проверка проводки, а не обработчиков.

    Сами handle_create_bot_name/token были написаны корректно — их просто
    никто не вызывал: в _register_handlers существовал единственный
    NewMessage, и тот на "/start". Тест структурный, потому что регистрация
    живёт в замыканиях и снаружи её иначе не увидеть.
    """
    import ast

    source = (ROOT / "services" / "ia-mother" / "bot.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    register = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_register_handlers"
    )
    body = ast.dump(register)

    # Должен быть NewMessage, не сводящийся к команде /start.
    new_message_calls = [
        node for node in ast.walk(register)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "NewMessage"
    ]
    assert len(new_message_calls) >= 2, "текстовые сообщения никто не слушает"

    assert "handle_create_bot_name" in body, "шаг с именем не подключён"
    assert "handle_create_bot_token" in body, "шаг с токеном не подключён"


def test_callback_patterns_do_not_overlap():
    """
    Один колбэк — один обработчик.

    Telethon компилирует `pattern` в re.match, то есть сравнение идёт по
    префиксу (в отличие от `data`, где оно точное). Без якоря "$" шаблон
    b"exchange" ловил ещё и exchange_stars_to_ia, exchange_history и все
    остальные, а b"marketplace" — весь marketplace_*: на одно нажатие
    срабатывало несколько экранов и они перетирали ответ друг друга.
    """
    import ast
    import re

    source = (ROOT / "services" / "ia-mother" / "bot.py").read_text(encoding="utf-8")

    patterns = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "CallbackQuery"):
            for keyword in node.keywords:
                if keyword.arg == "pattern" and isinstance(keyword.value, ast.Constant):
                    patterns.append(keyword.value.value)

    assert patterns, "обработчики колбэков не найдены"

    def payload_for(pattern: bytes) -> bytes:
        """Собрать пример данных кнопки, которые шаблон должен поймать."""
        sample = pattern.rstrip(b"$")
        sample = sample.replace(b"(.+)", b"abc")
        sample = sample.replace(rb"(stars|iam)", b"stars")
        sample = sample.replace(rb"(\d+)", b"100")
        return sample

    for pattern in patterns:
        payload = payload_for(pattern)
        matching = [p for p in patterns if re.compile(p).match(payload)]
        assert matching == [pattern], (
            f"колбэк {payload!r} ловят несколько обработчиков: {matching}"
        )
