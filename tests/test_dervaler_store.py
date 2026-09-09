"""Тесты SQLite-хранилища: сообщения, курсор, FTS-поиск и FAQ."""

from datetime import datetime, timezone

import pytest

from dervaler.store import Message, Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "archive.sqlite3")
    yield s
    s.close()


def msg(id_, text, chat_id=-100, sender="tester"):
    return Message(
        id=id_, chat_id=chat_id, date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sender_id=1, sender_name=sender, text=text, reply_to=None,
    )


def test_add_and_count(store):
    saved = store.add_messages(-100, [msg(1, "привет"), msg(2, "как дела")])
    assert saved == 2
    assert store.message_count(-100) == 2


def test_media_without_text_is_not_stored(store):
    assert store.add_messages(-100, [msg(1, None), msg(2, "  ")]) == 0
    assert store.message_count(-100) == 0


def test_duplicates_are_replaced_not_appended(store):
    store.add_messages(-100, [msg(1, "первый раз")])
    store.add_messages(-100, [msg(1, "обновлённый текст")])
    assert store.message_count(-100) == 1


def test_messages_are_scoped_by_chat(store):
    store.add_messages(-100, [msg(1, "в чате A")])
    store.add_messages(-200, [msg(1, "в чате B")])
    assert store.message_count(-100) == 1
    assert store.message_count(-200) == 1


def test_checkpoint_defaults_to_zero(store):
    assert store.get_checkpoint(-100) == 0


def test_checkpoint_updates(store):
    store.set_checkpoint(-100, 42)
    assert store.get_checkpoint(-100) == 42
    store.set_checkpoint(-100, 99)
    assert store.get_checkpoint(-100) == 99


def test_checkpoint_is_per_chat(store):
    store.set_checkpoint(-100, 10)
    store.set_checkpoint(-200, 20)
    assert store.get_checkpoint(-100) == 10
    assert store.get_checkpoint(-200) == 20


def test_fts_search_finds_message(store):
    store.add_messages(-100, [
        msg(1, "деплой делается через docker compose"),
        msg(2, "сегодня хорошая погода"),
    ])
    hits = store.search(-100, "деплой")
    assert len(hits) == 1
    assert "docker compose" in hits[0]["text"]


def test_fts_search_respects_chat(store):
    store.add_messages(-100, [msg(1, "секретный пароль")])
    store.add_messages(-200, [msg(1, "секретный пароль")])
    assert len(store.search(-100, "секретный")) == 1
    assert len(store.search(-200, "секретный")) == 1


def test_fts_search_empty_query(store):
    store.add_messages(-100, [msg(1, "что-то")])
    assert store.search(-100, "") == []


def test_fts_bad_query_does_not_raise(store):
    """Битый запрос (незакрытая кавычка) не должен ронять бота."""
    store.add_messages(-100, [msg(1, "текст")])
    assert store.search(-100, 'unbalanced " quote') == []


def test_recent_returns_newest_last(store):
    store.add_messages(-100, [msg(i, f"сообщение {i}") for i in range(1, 6)])
    recent = store.recent(-100, limit=3)
    assert [r["id"] for r in recent] == [3, 4, 5]


class TestFaq:
    def test_new_item_is_draft_by_default(self, store):
        faq_id = store.add_faq(-100, "Как деплоить?", "Через compose")
        item = store.get_faq(faq_id)
        assert item["status"] == "draft"

    def test_only_published_visible_by_default(self, store):
        store.add_faq(-100, "Вопрос A", "Ответ A", status="published")
        store.add_faq(-100, "Вопрос B", "Ответ B", status="draft")
        visible = store.list_faq(-100)
        assert len(visible) == 1
        assert visible[0]["question"] == "Вопрос A"

    def test_list_all_statuses(self, store):
        store.add_faq(-100, "A", "1", status="published")
        store.add_faq(-100, "B", "2", status="draft")
        assert len(store.list_faq(-100, status=None)) == 2

    def test_publish_changes_status(self, store):
        faq_id = store.add_faq(-100, "Вопрос", "Ответ")
        store.update_faq(faq_id, status="published", updated_by=555)
        assert store.get_faq(faq_id)["status"] == "published"
        assert store.get_faq(faq_id)["updated_by"] == 555

    def test_edit_question_and_answer(self, store):
        faq_id = store.add_faq(-100, "Старый вопрос", "Старый ответ", status="published")
        store.update_faq(faq_id, question="Новый вопрос", answer="Новый ответ")
        item = store.get_faq(faq_id)
        assert item["question"] == "Новый вопрос"
        assert item["answer"] == "Новый ответ"

    def test_update_missing_returns_false(self, store):
        assert store.update_faq(999, question="нет") is False

    def test_update_no_fields_returns_false(self, store):
        faq_id = store.add_faq(-100, "В", "О")
        assert store.update_faq(faq_id) is False

    def test_delete(self, store):
        faq_id = store.add_faq(-100, "В", "О")
        assert store.delete_faq(faq_id) is True
        assert store.get_faq(faq_id) is None
        assert store.delete_faq(faq_id) is False

    def test_search_faq_only_published(self, store):
        store.add_faq(-100, "Как деплоить?", "compose up", status="published")
        store.add_faq(-100, "Как деплоить (черновик)?", "секретно", status="draft")
        hits = store.search_faq(-100, "деплоить")
        assert len(hits) == 1
        assert hits[0]["answer"] == "compose up"

    def test_faq_is_scoped_by_chat(self, store):
        store.add_faq(-100, "Вопрос", "Ответ", status="published")
        assert len(store.list_faq(-200)) == 0

    def test_source_ids_roundtrip(self, store):
        faq_id = store.add_faq(-100, "В", "О", source_ids=[1, 2, 3], status="published")
        assert store.get_faq(faq_id)["source_message_ids"] == "[1, 2, 3]"


def test_store_reopen_persists(tmp_path):
    """Данные переживают перезапуск процесса."""
    path = tmp_path / "persist.sqlite3"
    s1 = Store(path)
    s1.add_messages(-100, [msg(1, "сохранено навсегда")])
    s1.set_checkpoint(-100, 1)
    s1.close()

    s2 = Store(path)
    assert s2.message_count(-100) == 1
    assert s2.get_checkpoint(-100) == 1
    s2.close()
