"""
SQLite-хранилище архива чата для Дервалера.

Схема:
  messages   — сырые сообщения архива
  chunks     — объединённые блоки для сводки (этап 3+)
  faq_items  — FAQ (черновики и опубликованные)
  checkpoints— курсор инжеста (last_ingested_id по чату)

Используется FTS5 для полнотекстового поиска без внешних зависимостей.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER NOT NULL,
    chat_id       INTEGER NOT NULL,
    date          TEXT NOT NULL,
    sender_id     INTEGER,
    sender_name   TEXT,
    text          TEXT,
    reply_to      INTEGER,
    ingested_at   TEXT NOT NULL,
    PRIMARY KEY (chat_id, id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    start_id    INTEGER NOT NULL,
    end_id      INTEGER NOT NULL,
    summary     TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faq_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id           INTEGER NOT NULL,
    question          TEXT NOT NULL,
    answer            TEXT NOT NULL,
    source_message_ids TEXT,
    status            TEXT NOT NULL DEFAULT 'draft',
    updated_by        INTEGER,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkpoints (
    chat_id          INTEGER PRIMARY KEY,
    last_ingested_id INTEGER NOT NULL DEFAULT 0,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_date ON messages(chat_id, date);
CREATE INDEX IF NOT EXISTS idx_faq_chat_status    ON faq_items(chat_id, status);

-- Полнотекстовый поиск по архиву (внешнее содержимое = таблица messages).
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    text,
    content='messages',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
"""

# Триггеры держат FTS-индекс в согласии с messages.
FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, text)
        VALUES ('delete', old.rowid, old.text);
END;
"""


@dataclass
class Message:
    """Сырое сообщение, сохранённое в архив."""

    id: int
    chat_id: int
    date: datetime
    sender_id: int | None
    sender_name: str | None
    text: str | None
    reply_to: int | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Стоп-слова: они не несут смысла и зашумляют выдачу bm25.
_STOPWORDS = {
    "что", "кто", "как", "где", "куда", "откуда", "когда", "почему", "зачем",
    "какой", "какая", "какое", "какие", "чей", "сколько", "можно", "ли",
    "это", "для", "про", "есть", "был", "была", "было", "были", "the", "a",
    "an", "is", "are", "was", "were", "to", "of", "in", "on", "for", "and",
    "or", "what", "who", "how", "where", "when", "why",
}


# Типичные русские окончания — отсекаем их, чтобы «деплоить» нашло «деплой».
# ВАЖНО: порядок по убыванию длины, иначе короткое окончание срежется
# раньше длинного и основы одного слова разойдутся.
_RU_ENDINGS = (
    "ами", "ями", "ого", "ему", "ому", "ыми", "ими", "ах", "ях", "ам", "ям",
    "ила", "ило", "или", "ать", "ять", "еть", "ить", "овать", "евать",
    "ая", "яя", "ое", "ее", "ой", "ей", "ый", "ий", "ью", "ия", "ии", "ию",
    "ть", "ла", "ло", "ли", "ет", "ут", "ют", "ат", "ят", "ем", "им", "ом",
    "ов", "ев", "у", "ю", "а", "я", "о", "е", "ы", "и", "й", "ь",
)


def _stem(word: str) -> str:
    """
    Грубый стеммер для русского: отсечь типичное окончание.

    Основу короче 4 символов не оставляем — иначе «деплой» и «деплоить»
    дадут разные основы и перестанут находиться друг через друга.
    """
    if len(word) <= 4:
        return word
    for ending in _RU_ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 4:
            return word[: -len(ending)]
    return word


def build_fts_query(query: str) -> str:
    """
    Превратить вопрос пользователя в безопасный запрос FTS5.

    «Как деплоить?» → «"депло"*»
    «деплой через docker» → «"депло"* OR "docker"*»

    Слова заключаем в кавычки, чтобы знаки препинания внутри них
    не воспринимались как синтаксис FTS. Стем + «*» даёт поиск
    и по префиксу, и по общей основе слова.
    """
    if not query:
        return ""
    words = re.findall(r"[\wёЁа-яА-Яa-zA-Z]+", query.lower())
    terms = [w for w in words if len(w) > 2 and w not in _STOPWORDS]
    if not terms:
        # Остались одни стоп-слова — ищем по ним, иначе не найдём ничего.
        terms = [w for w in words if len(w) > 1]
    if not terms:
        return ""
    stems = [_stem(t) for t in terms]
    # Убираем дубли, сохраняя порядок.
    seen, unique = set(), []
    for s in stems:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return " OR ".join(f'"{s}"*' for s in unique[:8])


class Store:
    """Обёртка над SQLite для архива чата."""

    def __init__(self, db_path: Path | str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.executescript(FTS_TRIGGERS)
        self._conn.commit()
        logger.info("Store ready at {}", self.path)

    def close(self) -> None:
        self._conn.close()

    # ── Сообщения ──

    def add_messages(self, chat_id: int, messages: Iterable[Message]) -> int:
        """Пакетная вставка сообщений. Возвращает количество записанных."""
        rows = [
            (
                m.id, chat_id, m.date.isoformat(), m.sender_id,
                m.sender_name, m.text, m.reply_to, _now(),
            )
            for m in messages
            # Медиа без подписи и сообщения из одних пробелов в архив не пишем.
            if m.text and m.text.strip()
        ]
        if not rows:
            return 0
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO messages
                (id, chat_id, date, sender_id, sender_name, text, reply_to, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def message_count(self, chat_id: int) -> int:
        cur = self._conn.execute(
            "SELECT COUNT(*) AS n FROM messages WHERE chat_id = ?", (chat_id,)
        )
        return cur.fetchone()["n"]

    # ── Чекпоинты ──

    def get_checkpoint(self, chat_id: int) -> int:
        """Курсор инжеста: максимальный id уже сохранённого сообщения."""
        cur = self._conn.execute(
            "SELECT last_ingested_id FROM checkpoints WHERE chat_id = ?", (chat_id,)
        )
        row = cur.fetchone()
        return row["last_ingested_id"] if row else 0

    def set_checkpoint(self, chat_id: int, last_id: int) -> None:
        """Сохранить курсор. Пишем после каждой пачки, чтобы рестарт не терял прогресс."""
        self._conn.execute(
            """
            INSERT INTO checkpoints (chat_id, last_ingested_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                last_ingested_id = excluded.last_ingested_id,
                updated_at = excluded.updated_at
            """,
            (chat_id, last_id, _now()),
        )
        self._conn.commit()

    # ── Поиск ──

    def search(self, chat_id: int, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Полнотекстовый поиск по архиву чата.

        Запрос пользователя очищается до набора слов: FTS5 падает на
        знаках препинания («деплой?» — это типичный вопрос), поэтому
        скобки/кавычки/вопросительные знаки отбрасываем, а слова
        объединяем через OR.
        """
        match_query = build_fts_query(query)
        if not match_query:
            return []
        try:
            cur = self._conn.execute(
                """
                SELECT m.id, m.date, m.sender_name, m.text
                FROM messages_fts f
                JOIN messages m ON m.rowid = f.rowid
                WHERE messages_fts MATCH ? AND m.chat_id = ?
                ORDER BY bm25(messages_fts)
                LIMIT ?
                """,
                (match_query, chat_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]
        except sqlite3.OperationalError as e:
            # Непредвиденный битый запрос не должен ронять бота.
            logger.warning("FTS query failed ({}): {}", query[:50], e)
            return []

    def recent(self, chat_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """Последние сообщения чата (для контекста сводки)."""
        cur = self._conn.execute(
            """
            SELECT id, date, sender_name, text
            FROM messages WHERE chat_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (chat_id, limit),
        )
        return [dict(r) for r in reversed(cur.fetchall())]

    # ── Сводка чата ──

    def save_summary(self, chat_id: int, start_id: int, end_id: int, summary: str) -> int:
        """Записать новую актуальную сводку чата."""
        cur = self._conn.execute(
            """
            INSERT INTO chunks (chat_id, start_id, end_id, summary, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, start_id, end_id, summary, _now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_summary(self, chat_id: int) -> str | None:
        """Текущая (последняя) сводка чата."""
        cur = self._conn.execute(
            """
            SELECT summary FROM chunks
            WHERE chat_id = ? ORDER BY id DESC LIMIT 1
            """,
            (chat_id,),
        )
        row = cur.fetchone()
        return row["summary"] if row else None

    # ── FAQ ──

    def add_faq(
        self,
        chat_id: int,
        question: str,
        answer: str,
        source_ids: list[int] | None = None,
        status: str = "draft",
        updated_by: int | None = None,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO faq_items
                (chat_id, question, answer, source_message_ids, status, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id, question, answer,
                json.dumps(source_ids or []), status, updated_by, _now(),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_faq(
        self,
        faq_id: int,
        question: str | None = None,
        answer: str | None = None,
        status: str | None = None,
        updated_by: int | None = None,
    ) -> bool:
        """Частичное обновление FAQ. Возвращает False если записи нет."""
        fields, values = [], []
        if question is not None:
            fields.append("question = ?")
            values.append(question)
        if answer is not None:
            fields.append("answer = ?")
            values.append(answer)
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if not fields:
            return False
        fields.append("updated_by = ?")
        values.append(updated_by)
        fields.append("updated_at = ?")
        values.append(_now())
        values.append(faq_id)

        cur = self._conn.execute(
            f"UPDATE faq_items SET {', '.join(fields)} WHERE id = ?", values
        )
        self._conn.commit()
        return cur.rowcount > 0

    def delete_faq(self, faq_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM faq_items WHERE id = ?", (faq_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def get_faq(self, faq_id: int) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT * FROM faq_items WHERE id = ?", (faq_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_faq(self, chat_id: int, status: str | None = "published") -> list[dict[str, Any]]:
        """Список FAQ. По умолчанию — только опубликованные."""
        if status is None:
            cur = self._conn.execute(
                "SELECT * FROM faq_items WHERE chat_id = ? ORDER BY id", (chat_id,)
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM faq_items WHERE chat_id = ? AND status = ? ORDER BY id",
                (chat_id, status),
            )
        return [dict(r) for r in cur.fetchall()]

    def search_faq(self, chat_id: int, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """
        Поиск по опубликованному FAQ.

        Ищем по основам слов (как в search), а не точной подстрокой:
        вопрос «как деплоить?» должен находить запись «Как деплоить?».
        """
        # Берём слова запроса как есть (без стемминга) и ищем каждое
        # как подстроку — так «как деплоить?» находит «Как деплоить?».
        # Стоп-слова отбрасываем: иначе «как» не даст совпадения.
        words = re.findall(r"[\wёЁа-яА-Яa-zA-Z]+", (query or "").lower())
        terms = [w for w in words if len(w) > 2 and w not in _STOPWORDS]
        if not terms:
            terms = [w for w in words if len(w) > 1]
        if not terms:
            return []

        # Собираем условие: каждое слово должно встретиться в вопросе или ответе.
        conditions, params = [], []
        for term in terms[:8]:
            conditions.append("(LOWER(question) LIKE ? OR LOWER(answer) LIKE ?)")
            params.extend([f"%{term}%", f"%{term}%"])

        cur = self._conn.execute(
            f"""
            SELECT * FROM faq_items
            WHERE chat_id = ? AND status = 'published'
              AND {' AND '.join(conditions)}
            LIMIT ?
            """,
            [chat_id, *params, limit],
        )
        return [dict(r) for r in cur.fetchall()]
