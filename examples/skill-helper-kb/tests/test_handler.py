"""
Тесты helper-kb. Telegram не нужен: хранилище — реальный SQLite во временной
папке, клиент подменяется фейком.

Главное, что проверяем:
  — FAQ редактируют только админы/владелец (ACL);
  — черновики не видны в /faq и не используются как ответы;
  — на болтовню скилл молчит (skip), а не отвечает «не нашёл»;
  — ответ собирается из FAQ и из архива.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "examples" / "skill-helper-kb"
sys.path.insert(0, str(ROOT / "sdk"))
sys.path.insert(0, str(ROOT / "services"))

# Скилл лежит как пакет-каталог, импортируем по пути.
_spec = importlib.util.spec_from_file_location(
    "helper_kb_handler", SKILL_DIR / "handler.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["helper_kb_handler"] = _mod
_spec.loader.exec_module(_mod)

HelperKbSkill = _mod.HelperKbSkill

from dervaler.store import Message, Store  # noqa: E402
from zero_bot_sdk import SkillContext, SkillResponse  # noqa: E402

CHAT_ID = -100123


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "kb.sqlite3")
    yield s
    s.close()


@pytest.fixture
def skill(store):
    return HelperKbSkill(store=store, telegram_client=None)


@pytest.fixture
def admin_ctx(monkeypatch):
    """Контекст от имени администратора чата."""
    monkeypatch.setattr(_mod, "can_manage_faq", _allow)
    return SkillContext.for_testing(chat_id=CHAT_ID, user_id=555, config={})


@pytest.fixture
def user_ctx(monkeypatch):
    """Контекст от имени обычного участника."""
    monkeypatch.setattr(_mod, "can_manage_faq", _deny)
    return SkillContext.for_testing(chat_id=CHAT_ID, user_id=777, config={})


async def _allow(client, chat_id, user_id, is_private=False):
    return True


async def _deny(client, chat_id, user_id, is_private=False):
    return False


def seed_archive(store, texts):
    """Заполнить архив сообщениями."""
    from datetime import datetime, timezone

    store.add_messages(
        CHAT_ID,
        [
            Message(
                id=i, chat_id=CHAT_ID,
                date=datetime(2026, 1, i % 28 + 1, tzinfo=timezone.utc),
                sender_id=1, sender_name="tester", text=t, reply_to=None,
            )
            for i, t in enumerate(texts, start=1)
        ],
    )


# ── /faq ──

@pytest.mark.asyncio
async def test_faq_empty(skill, admin_ctx):
    resp = await skill.on_command(admin_ctx, "/faq", "")
    assert resp.text == "📋 FAQ пока пуст."


@pytest.mark.asyncio
async def test_faq_shows_only_published(skill, admin_ctx, store):
    store.add_faq(CHAT_ID, "Опубликованный?", "Публичный ответ", status="published")
    store.add_faq(CHAT_ID, "Черновик?", "Скрытый ответ", status="draft")

    resp = await skill.on_command(admin_ctx, "/faq", "")

    assert "Публичный ответ" in resp.text
    assert "Скрытый ответ" not in resp.text


# ── ACL: только админы ──

@pytest.mark.asyncio
async def test_admin_can_add_faq(skill, admin_ctx, store):
    resp = await skill.on_command(
        admin_ctx, "/faq_add", "Как деплоить? | docker compose up -d"
    )
    assert "✅" in resp.text
    assert len(store.list_faq(CHAT_ID, status=None)) == 1


@pytest.mark.asyncio
async def test_regular_user_cannot_add_faq(skill, user_ctx, store):
    resp = await skill.on_command(
        user_ctx, "/faq_add", "Вопрос? | Ответ"
    )
    assert "⛔" in resp.text or "администратор" in resp.text
    assert len(store.list_faq(CHAT_ID, status=None)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command,args",
    [
        ("/faq_add", "В | О"),
        ("/faq_edit", "1 | новый"),
        ("/faq_del", "1"),
        ("/faq_publish", "1"),
    ],
)
async def test_all_faq_admin_commands_are_acl_protected(
    skill, user_ctx, store, command, args
):
    """Ни одна команда управления не должна проходить мимо проверки прав."""
    store.add_faq(CHAT_ID, "В", "О", status="draft")
    resp = await skill.on_command(user_ctx, command, args)
    assert "⛔" in resp.text or "администратор" in resp.text


@pytest.mark.asyncio
async def test_unknown_command_skips(skill, admin_ctx):
    resp = await skill.on_command(admin_ctx, "/unknown", "")
    assert resp.is_skip()


@pytest.mark.asyncio
async def test_command_with_bot_suffix_is_normalized(skill, admin_ctx, store):
    """/faq@MyBot должен работать так же, как /faq."""
    store.add_faq(CHAT_ID, "В?", "О", status="published")
    resp = await skill.on_command(admin_ctx, "/faq@MyBot", "")
    assert "О" in resp.text


# ── Жизненный цикл черновика ──

@pytest.mark.asyncio
async def test_draft_becomes_visible_after_publish(skill, admin_ctx, store):
    add = await skill.on_command(admin_ctx, "/faq_add", "Вопрос? | Ответ")
    faq_id = add.text.split("#")[1].split()[0]

    # До публикации — не виден.
    assert "Ответ" not in (await skill.on_command(admin_ctx, "/faq", "")).text

    await skill.on_command(admin_ctx, "/faq_publish", faq_id)

    assert "Ответ" in (await skill.on_command(admin_ctx, "/faq", "")).text


@pytest.mark.asyncio
async def test_publish_records_editor(skill, admin_ctx, store):
    add = await skill.on_command(admin_ctx, "/faq_add", "В? | О")
    faq_id = int(add.text.split("#")[1].split()[0])
    await skill.on_command(admin_ctx, "/faq_publish", faq_id)
    assert store.get_faq(faq_id)["updated_by"] == 555


@pytest.mark.asyncio
async def test_edit_updates_answer(skill, admin_ctx, store):
    add = await skill.on_command(admin_ctx, "/faq_add", "В? | старый")
    faq_id = add.text.split("#")[1].split()[0]
    await skill.on_command(admin_ctx, "/faq_edit", f"{faq_id} | новый")
    assert store.get_faq(int(faq_id))["answer"] == "новый"


@pytest.mark.asyncio
async def test_delete_removes_item(skill, admin_ctx, store):
    add = await skill.on_command(admin_ctx, "/faq_add", "В? | О")
    faq_id = add.text.split("#")[1].split()[0]
    assert await skill.on_command(admin_ctx, "/faq_del", faq_id)
    assert store.get_faq(int(faq_id)) is None


@pytest.mark.asyncio
async def test_delete_missing_reports_error(skill, admin_ctx, store):
    resp = await skill.on_command(admin_ctx, "/faq_del", "999")
    assert "❌" in resp.text


# ── Валидация формата ──

@pytest.mark.asyncio
async def test_faq_add_requires_separator(skill, admin_ctx, store):
    resp = await skill.on_command(admin_ctx, "/faq_add", "без разделителя")
    assert "Формат" in resp.text
    assert len(store.list_faq(CHAT_ID, status=None)) == 0


@pytest.mark.asyncio
async def test_faq_add_rejects_empty_half(skill, admin_ctx, store):
    assert "Формат" in (await skill.on_command(admin_ctx, "/faq_add", "В? |")).text
    assert "Формат" in (await skill.on_command(admin_ctx, "/faq_add", "| О")).text
    assert len(store.list_faq(CHAT_ID, status=None)) == 0


@pytest.mark.asyncio
async def test_faq_edit_requires_numeric_id(skill, admin_ctx, store):
    resp = await skill.on_command(admin_ctx, "/faq_edit", "не_число | текст")
    assert "Формат" in resp.text


@pytest.mark.asyncio
async def test_faq_publish_requires_numeric_id(skill, admin_ctx, store):
    assert "Формат" in (await skill.on_command(admin_ctx, "/faq_publish", "x")).text


# ── Ответы на сообщения ──

@pytest.mark.asyncio
@pytest.mark.parametrize("text", [
    "привет всем, как дела",
    # С вопросительным знаком — тот же смысл, но раньше это считалось
    # вопросом, поиск по архиву цеплялся за «привет»/«дела», и бот отвечал
    # на приветствие случайными цитатами из истории.
    "привет всем, как дела?",
    "доброе утро",
    "спасибо!",
    "кто тут?",
])
async def test_chatter_is_skipped(skill, user_ctx, store, text):
    """На обычную болтовню скилл молчит, даже если в архиве есть те же слова."""
    seed_archive(store, ["Всем привет, я новенькая", "деплой делается через docker"])
    resp = await skill.on_message(user_ctx, text)
    assert resp.is_skip()


@pytest.mark.asyncio
async def test_question_with_empty_kb_is_skipped_in_group(skill, user_ctx):
    """В группе без найденного — молчим, а не спамим «не нашёл»."""
    user_ctx.config["is_private"] = False
    resp = await skill.on_message(user_ctx, "Как деплоить?")
    assert resp.is_skip()


@pytest.mark.asyncio
async def test_question_with_empty_kb_answers_in_private(skill, user_ctx):
    """В личке честно говорим, что не нашли."""
    user_ctx.config["is_private"] = True
    resp = await skill.on_message(user_ctx, "Как деплоить?")
    assert "Не нашёл" in resp.text


@pytest.mark.asyncio
async def test_question_finds_archive(skill, user_ctx, store):
    seed_archive(store, ["деплой делается через docker compose up -d"])
    resp = await skill.on_message(user_ctx, "как деплоить?")
    assert resp.has_content()
    assert "docker compose" in resp.text


@pytest.mark.asyncio
async def test_faq_answer_preferred_over_archive(skill, user_ctx, store):
    """Если есть FAQ — отвечаем им, а не сырыми цитатами."""
    seed_archive(store, ["какой-то старый разговор про деплой"])
    store.add_faq(CHAT_ID, "Как деплоить?", "Ответ из FAQ", status="published")

    resp = await skill.on_message(user_ctx, "как деплоить?")

    assert "Ответ из FAQ" in resp.text


@pytest.mark.asyncio
async def test_draft_faq_is_not_used_as_answer(skill, user_ctx, store):
    """Неопубликованный черновик не должен попадать в ответы."""
    store.add_faq(CHAT_ID, "Как деплоить?", "Секретный черновик", status="draft")
    # В группе: черновик не найден → скилл молчит (skip), а не выдаёт ответ.
    user_ctx.config["is_private"] = False
    resp = await skill.on_message(user_ctx, "как деплоить?")
    assert resp.is_skip()

    # В личке: ответ есть, но без текста черновика.
    user_ctx.config["is_private"] = True
    resp = await skill.on_message(user_ctx, "как деплоить?")
    assert "Секретный черновик" not in (resp.text or "")


@pytest.mark.asyncio
async def test_ask_command_works_without_question_mark(skill, user_ctx, store):
    seed_archive(store, ["пароль от админки лежит в vault"])
    resp = await skill.on_command(user_ctx, "/ask", "пароль от админки")
    assert "vault" in resp.text


@pytest.mark.asyncio
async def test_ask_without_args_asks_for_question(skill, user_ctx):
    resp = await skill.on_command(user_ctx, "/ask", "")
    assert "Напиши вопрос" in resp.text


@pytest.mark.asyncio
async def test_long_messages_are_truncated(skill, user_ctx, store):
    seed_archive(store, ["деплой " + "очень длинное слово " * 50])
    resp = await skill.on_message(user_ctx, "деплой?")
    assert len(resp.text) < 2000
    assert "…" in resp.text


# ── Статус инжеста ──

@pytest.mark.asyncio
async def test_ingest_status_reports_counts(skill, admin_ctx, store):
    seed_archive(store, ["раз", "два", "три"])
    store.set_checkpoint(CHAT_ID, 3)
    store.add_faq(CHAT_ID, "В", "О", status="published")
    store.add_faq(CHAT_ID, "В2", "О2", status="draft")

    resp = await skill.on_command(admin_ctx, "/ingest_status", "")

    assert "3" in resp.text
    assert "1" in resp.text  # опубликовано


# ── Устойчивость ──

@pytest.mark.asyncio
async def test_skill_without_store_skips_message():
    """Без базы знаний скилл не должен падать."""
    s = HelperKbSkill(store=None, telegram_client=None)
    ctx = SkillContext.for_testing(chat_id=CHAT_ID)
    resp = await s.on_message(ctx, "как деплоить?")
    assert resp.is_skip()


@pytest.mark.asyncio
async def test_skill_without_store_reports_on_faq():
    s = HelperKbSkill(store=None, telegram_client=None)
    ctx = SkillContext.for_testing(chat_id=CHAT_ID)
    resp = await s.on_command(ctx, "/faq", "")
    assert "не подключена" in resp.text or "пуст" in resp.text
