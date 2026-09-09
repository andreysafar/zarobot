"""
Живая сводка чата: Дервалер копит новые сообщения и раз в N штук
(или раз в T секунд) пересчитывает компактную сводку через LLM.

Debounce нужен, чтобы не дёргать модель на каждое сообщение в шумном чате.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone

from loguru import logger


class ChatSummarizer:
    """
    Накапливает новые сообщения и обновляет сводку чата.

    Сводка пишется в таблицу chunks (start_id..end_id) — по одной актуальной
    записи на чат, последняя по id считается текущей.
    """

    def __init__(self, store, llm_call=None, chat_id: int = 0):
        self.store = store
        self.chat_id = chat_id
        # llm_call(system_prompt, user_prompt) -> str; подменяется в тестах.
        self._llm = llm_call
        self._pending: list[dict] = []
        self._last_flush = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()
        # Пороги срабатывания.
        self.batch_size = int(os.getenv("SUMMARY_BATCH_SIZE", "20"))
        self.max_wait = float(os.getenv("SUMMARY_MAX_WAIT", "300"))
        self.enabled = os.getenv("SUMMARY_ENABLED", "true").lower() in ("1", "true", "yes")
        self._summary_prompt = ""

    def set_prompt(self, prompt: str) -> None:
        """Задать промпт сводки (берётся из личности Дервалера)."""
        self._summary_prompt = prompt

    async def add(self, message: dict) -> None:
        """Добавить сообщение в очередь на пересчёт сводки."""
        if not self.enabled:
            return
        async with self._lock:
            self._pending.append(message)
            due_by_count = len(self._pending) >= self.batch_size
            waited = (datetime.now(timezone.utc) - self._last_flush).total_seconds()
            due_by_time = waited >= self.max_wait

        if due_by_count or due_by_time:
            await self.flush()

    async def flush(self, force: bool = False) -> bool:
        """
        Пересчитать сводку по накопленным сообщениям.

        Возвращает True, если сводка обновлена.
        """
        if not self.enabled and not force:
            return False

        async with self._lock:
            if not self._pending:
                return False
            pending, self._pending = self._pending, []
            self._last_flush = datetime.now(timezone.utc)

        try:
            summary = await self._build_summary(pending)
        except Exception as e:
            logger.error("Не удалось обновить сводку: {}", e)
            # Сообщения теряем осознанно: сводка вспомогательная,
            # сырой архив уже надёжно сохранён инжестом.
            return False

        if not summary:
            return False

        start_id = min(m["id"] for m in pending if m.get("id") is not None)
        end_id = max(m["id"] for m in pending if m.get("id") is not None)
        self.store.save_summary(self.chat_id, start_id, end_id, summary)
        logger.info("Сводка чата {} обновлена ({}..{})", self.chat_id, start_id, end_id)
        return True

    async def _build_summary(self, messages: list[dict]) -> str | None:
        """Собрать новую сводку: предыдущая + новые сообщения → LLM."""
        if self._llm is None:
            return None

        previous = self.store.get_summary(self.chat_id) or "Сводка пока пуста."
        block = "\n".join(
            f"[{m.get('date', '')[:16]}] {m.get('sender_name') or 'участник'}: {m.get('text')}"
            for m in messages
        )
        prompt = (
            f"{self._summary_prompt}\n\n"
            f"ПРЕДЫДУЩАЯ СВОДКА:\n{previous}\n\n"
            f"НОВЫЕ СООБЩЕНИЯ:\n{block}"
        )
        result = await self._llm(prompt)
        return (result or "").strip() or None

    @property
    def pending(self) -> int:
        return len(self._pending)


def parse_summary_json(raw: str) -> dict:
    """
    Достать JSON из ответа модели.

    Модели часто оборачивают JSON в ```json ... ``` — снимаем обёртку.
    """
    if not raw:
        return {}
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
