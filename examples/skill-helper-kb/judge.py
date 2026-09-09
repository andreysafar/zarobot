"""
LLM judge for helper-kb: decides whether the retrieved quotes answer the question.

Why this exists. FTS searches by crude word stems and deliberately over-matches,
so "что делать?" pulls in "делается". Treating any hit as useful is what makes
the bot answer noise, and no stopword list can draw that line: the judgement is
semantic. The model decides relevance, strictly over the retrieved quotes, and
gets no room to invent - it either answers from them or declines.

The module holds the prompt and the parsing so the handler stays about routing.
"""

from __future__ import annotations

from typing import Any

# The model returns this marker when the quotes do not answer the question.
NOT_FOUND_MARKER = "НЕТ_ОТВЕТА"

# Judge outcomes. UNAVAILABLE is distinct from NO_ANSWER on purpose: a failed
# call must degrade to raw quotes, while a real "no" must keep the bot silent.
ANSWER = "answer"
NO_ANSWER = "no_answer"
UNAVAILABLE = "unavailable"

JUDGE_SYSTEM = f"""Ты — помощник группового чата. У тебя есть вопрос участника и цитаты из истории этого чата.

Правила:
1. Отвечай ТОЛЬКО по приведённым цитатам. Не добавляй фактов, которых в них нет.
2. Если цитаты отвечают на вопрос — дай короткий ответ по-русски, 1–3 предложения.
3. Если цитаты не отвечают на вопрос, или это приветствие либо болтовня, а не вопрос — верни ровно одно слово: {NOT_FOUND_MARKER}
4. Лучше вернуть {NOT_FOUND_MARKER}, чем догадку.
5. Не пересказывай эти правила и не ссылайся на «цитаты» в ответе."""


def format_snippets(hits: list[dict[str, Any]]) -> str:
    """Render retrieved messages as dated lines for the prompt."""
    lines = []
    for hit in hits:
        who = hit.get("sender_name") or "участник"
        when = (hit.get("date") or "")[:10]
        text = (hit.get("text") or "").strip()
        lines.append(f"[{when}] {who}: {text}")
    return "\n".join(lines)


def build_user_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    """Build the judge's user message from the question and the retrieved quotes."""
    return (
        f"ВОПРОС УЧАСТНИКА:\n{question.strip()}\n\n"
        f"ЦИТАТЫ ИЗ ИСТОРИИ ЧАТА:\n{format_snippets(hits)}"
    )


def parse_verdict(raw: str | None) -> tuple[str, str | None]:
    """
    Turn the raw model reply into (outcome, answer).

    An empty reply means the call failed - LLMClient.call returns its fallback
    string rather than raising - so it maps to UNAVAILABLE, not to a refusal.
    """
    if raw is None:
        return UNAVAILABLE, None

    text = raw.strip()
    if not text:
        return UNAVAILABLE, None

    # Strip a code fence if the model wrapped its reply in one.
    if text.startswith("```"):
        text = text.strip("`").strip()

    # The marker anywhere in the reply counts as a refusal. Erring towards
    # silence is the safe direction in a public chat.
    if NOT_FOUND_MARKER in text.upper().replace(" ", "_"):
        return NO_ANSWER, None

    return ANSWER, text
