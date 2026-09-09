"""
Контракт судьи: что бот делает при каждом исходе работы модели.

Тут проверяется поведение, а не словарь: модель подменена заглушкой, и нас
интересует, молчит ли бот при отказе судьи, деградирует ли до цитат при
недоступной модели и не утекает ли в промпт то, чего в нём быть не должно.
"""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from zero_bot_sdk import SkillContext

SKILL_DIR = Path(__file__).resolve().parents[1]


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SKILL_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


judge = _load("helper_kb_judge_test", "judge.py")
handler_mod = _load("helper_kb_handler_judge", "handler.py")
HelperKbSkill = handler_mod.HelperKbSkill

CHAT = -1001234567890
ARCHIVE = [
    "Деплой делается командой docker compose up -d --build",
    "Ретроспектива назначена на пятницу",
]


class StubLLM:
    """Заглушка модели: отдаёт заданный ответ и запоминает промпты."""

    def __init__(self, reply=None, raises=None):
        self.reply = reply
        self.raises = raises
        self.calls = []

    async def __call__(self, system, user):
        self.calls.append({"system": system, "user": user})
        if self.raises is not None:
            raise self.raises
        return self.reply


@pytest.fixture
def store(tmp_path):
    from dervaler.store import Message, Store

    s = Store(tmp_path / "kb.sqlite3")
    s.add_messages(CHAT, [
        Message(id=i, chat_id=CHAT, date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                sender_id=1, sender_name="Аня", text=text, reply_to=None)
        for i, text in enumerate(ARCHIVE, start=1)
    ])
    yield s
    s.close()


def ctx(is_private=False):
    return SkillContext(bot_id="test", user_id=777, chat_id=CHAT,
                        config={"is_private": is_private})


# ── Исходы работы судьи ──

async def test_judge_answer_replaces_raw_quotes(store):
    """Когда судья ответил — отдаём его ответ, а не список цитат."""
    llm = StubLLM(reply="Деплой: docker compose up -d --build")
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(), "как деплоить?")

    assert resp.text == "Деплой: docker compose up -d --build"
    assert "Нашёл в истории чата" not in resp.text
    assert len(llm.calls) == 1


async def test_judge_refusal_keeps_bot_silent_in_group(store):
    """Судья сказал «не отвечают» — в группе молчим, хотя FTS что-то нашёл."""
    llm = StubLLM(reply=judge.NOT_FOUND_MARKER)
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(), "что делать?")

    assert resp.is_skip()


async def test_judge_refusal_answers_in_private(store):
    llm = StubLLM(reply=judge.NOT_FOUND_MARKER)
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(is_private=True), "что делать?")

    assert "Не нашёл" in resp.text


async def test_marker_never_leaks_to_the_user(store):
    llm = StubLLM(reply=f"  {judge.NOT_FOUND_MARKER}  ")
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(is_private=True), "как деплоить?")

    assert judge.NOT_FOUND_MARKER not in resp.text


# ── Деградация ──

async def test_broken_judge_degrades_to_quotes(store):
    """Модель упала — бот не замолкает, а отдаёт цитаты, как раньше."""
    llm = StubLLM(raises=RuntimeError("провайдер лёг"))
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(), "как деплоить?")

    assert "Нашёл в истории чата" in resp.text
    assert "docker compose up -d --build" in resp.text


async def test_empty_reply_is_treated_as_failure_not_refusal(store):
    """
    LLMClient.call возвращает fallback, а не бросает исключение.

    Пустой ответ значит «все провайдеры отказали» — это деградация до цитат,
    а не отказ судьи, иначе упавший OpenRouter молча выключил бы бота.
    """
    skill = HelperKbSkill(store=store, llm_call=StubLLM(reply=""))

    resp = await skill.on_message(ctx(), "как деплоить?")

    assert "Нашёл в истории чата" in resp.text


async def test_no_llm_configured_keeps_lexical_behaviour(store):
    skill = HelperKbSkill(store=store, llm_call=None)

    resp = await skill.on_message(ctx(), "как деплоить?")

    assert "Нашёл в истории чата" in resp.text


# ── Что видит судья ──

async def test_judge_gets_question_and_retrieved_quotes(store):
    llm = StubLLM(reply="ответ")
    skill = HelperKbSkill(store=store, llm_call=llm)

    await skill.on_message(ctx(), "как деплоить?")

    prompt = llm.calls[0]["user"]
    assert "как деплоить?" in prompt
    assert "docker compose up -d --build" in prompt


async def test_draft_faq_never_reaches_the_judge(store):
    """Черновик не источник ответа — он не должен попадать и в промпт."""
    store.add_faq(CHAT, "Как деплоить?", "СЕКРЕТНЫЙ ЧЕРНОВИК", status="draft")
    llm = StubLLM(reply="ответ")
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(), "как деплоить?")

    assert "СЕКРЕТНЫЙ ЧЕРНОВИК" not in llm.calls[0]["user"]
    assert "СЕКРЕТНЫЙ ЧЕРНОВИК" not in (resp.text or "")


async def test_published_faq_answers_without_calling_the_judge(store):
    """FAQ ведут админы — перепроверять его моделью незачем."""
    store.add_faq(CHAT, "Как деплоить?", "Ответ из FAQ", status="published")
    llm = StubLLM(reply="ответ судьи")
    skill = HelperKbSkill(store=store, llm_call=llm)

    resp = await skill.on_message(ctx(), "как деплоить?")

    assert "Ответ из FAQ" in resp.text
    assert llm.calls == []


async def test_judge_not_called_when_nothing_retrieved(store):
    """Пустая выдача — не тратим вызов модели."""
    llm = StubLLM(reply="ответ")
    skill = HelperKbSkill(store=store, llm_call=llm)

    await skill.on_message(ctx(), "какая политика отпусков?")

    assert llm.calls == []


# ── Разбор вердикта ──

@pytest.mark.parametrize("raw,expected", [
    (None, judge.UNAVAILABLE),
    ("", judge.UNAVAILABLE),
    ("   ", judge.UNAVAILABLE),
    ("НЕТ_ОТВЕТА", judge.NO_ANSWER),
    ("нет_ответа", judge.NO_ANSWER),
    ("НЕТ ОТВЕТА", judge.NO_ANSWER),
    ("```НЕТ_ОТВЕТА```", judge.NO_ANSWER),
    ("Деплой через docker compose.", judge.ANSWER),
])
def test_parse_verdict(raw, expected):
    outcome, _ = judge.parse_verdict(raw)
    assert outcome == expected
