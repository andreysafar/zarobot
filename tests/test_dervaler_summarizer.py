"""Тесты живой сводки чата: debounce, обновление, устойчивость."""

import os

import pytest

from dervaler.store import Store
from dervaler.summarizer import ChatSummarizer, parse_summary_json


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "sum.sqlite3")
    yield s
    s.close()


def make_summarizer(store, llm=None, **kw):
    s = ChatSummarizer(store, llm_call=llm, chat_id=-100)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def msg(i, text):
    return {"id": i, "date": "2026-01-01T10:00:00", "sender_name": "u", "text": text}


async def fake_llm(prompt):
    return "Обновлённая сводка."


def test_no_summary_initially(store):
    assert store.get_summary(-100) is None


@pytest.mark.asyncio
async def test_summary_saved_after_batch(store):
    """Накопили batch_size — сводка пересчиталась."""
    s = make_summarizer(store, llm=fake_llm, batch_size=2)
    await s.add(msg(1, "первое"))
    assert store.get_summary(-100) is None  # ещё рано
    await s.add(msg(2, "второе"))
    assert store.get_summary(-100) == "Обновлённая сводка."


@pytest.mark.asyncio
async def test_pending_cleared_after_flush(store):
    s = make_summarizer(store, llm=fake_llm, batch_size=2)
    await s.add(msg(1, "а"))
    await s.add(msg(2, "б"))
    assert s.pending == 0


@pytest.mark.asyncio
async def test_flush_empty_is_noop(store):
    s = make_summarizer(store, llm=fake_llm)
    assert await s.flush() is False


@pytest.mark.asyncio
async def test_flush_force_works_when_disabled(store):
    """Даже с выключенной сводкой force должен досчитать остаток."""
    s = make_summarizer(store, llm=fake_llm, enabled=False)
    s._pending.append(msg(1, "а"))
    assert await s.flush(force=True) is True
    assert store.get_summary(-100) == "Обновлённая сводка."


@pytest.mark.asyncio
async def test_disabled_summarizer_ignores_messages(store):
    s = make_summarizer(store, llm=fake_llm, enabled=False, batch_size=1)
    await s.add(msg(1, "а"))
    assert s.pending == 0
    assert store.get_summary(-100) is None


@pytest.mark.asyncio
async def test_llm_failure_keeps_old_summary(store):
    """Если LLM упал — старая сводка остаётся, процесс не падает."""
    store.save_summary(-100, 1, 1, "Старая сводка.")

    async def boom(prompt):
        raise RuntimeError("LLM недоступен")

    s = make_summarizer(store, llm=boom, batch_size=1)
    s._pending.append(msg(2, "б"))
    assert await s.flush() is False
    assert store.get_summary(-100) == "Старая сводка."


@pytest.mark.asyncio
async def test_no_llm_means_no_summary(store):
    s = make_summarizer(store, llm=None, batch_size=1)
    await s.add(msg(1, "а"))
    assert store.get_summary(-100) is None


@pytest.mark.asyncio
async def test_summary_ranges_saved(store):
    s = make_summarizer(store, llm=fake_llm, batch_size=3)
    for i in (5, 6, 7):
        await s.add(msg(i, f"сообщение {i}"))

    cur = store._conn.execute(
        "SELECT start_id, end_id FROM chunks WHERE chat_id=-100 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert (cur["start_id"], cur["end_id"]) == (5, 7)


@pytest.mark.asyncio
async def test_get_summary_returns_latest(store):
    s = make_summarizer(store, llm=fake_llm, batch_size=1)
    store.save_summary(-100, 1, 1, "Первая.")
    store.save_summary(-100, 2, 5, "Вторая.")
    assert store.get_summary(-100) == "Вторая."


@pytest.mark.asyncio
async def test_previous_summary_is_passed_to_llm(store):
    """Новая сводка должна учитывать предыдущую, иначе теряем контекст."""
    store.save_summary(-100, 1, 1, "ПРЕДЫДУЩАЯ.")
    seen = {}

    async def spy(prompt):
        seen["prompt"] = prompt
        return "Новая."

    s = make_summarizer(store, llm=spy, batch_size=1)
    await s.add(msg(2, "новое сообщение"))

    assert "ПРЕДЫДУЩАЯ." in seen["prompt"]
    assert "новое сообщение" in seen["prompt"]


@pytest.mark.asyncio
async def test_prompt_from_personality_used(store):
    seen = {}

    async def spy(prompt):
        seen["prompt"] = prompt
        return "ok"

    s = make_summarizer(store, llm=spy, batch_size=1)
    s.set_prompt("СПЕЦИАЛЬНЫЙ ПРОМПТ")
    await s.add(msg(1, "а"))
    assert "СПЕЦИАЛЬНЫЙ ПРОМПТ" in seen["prompt"]


class TestParseSummaryJson:
    def test_plain_json(self):
        assert parse_summary_json('{"Summary": "x"}') == {"Summary": "x"}

    def test_fenced_json(self):
        raw = '```json\n{"Summary": "x"}\n```'
        assert parse_summary_json(raw) == {"Summary": "x"}

    def test_fenced_without_lang(self):
        assert parse_summary_json('```\n{"Summary": "x"}\n```') == {"Summary": "x"}

    def test_invalid_returns_empty(self):
        assert parse_summary_json("не json") == {}

    def test_empty_returns_empty(self):
        assert parse_summary_json("") == {}

    def test_non_dict_returns_empty(self):
        assert parse_summary_json("[1,2]") == {}
