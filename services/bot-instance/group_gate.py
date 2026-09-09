"""
Group gating for the helper bot.

In a public chat the bot must stay silent on ordinary chatter and speak only
when it is addressed. This module centralises that decision so handlers and
skills share one rule set.

Speak when:
  * the message is a /command carrying our (optional) bot username suffix;
  * the bot is mentioned by @username, by activation phrase (personality),
    or is addressed by first name;
  * the message is a reply to one of the bot's own messages;
  * the message is a question (heuristic) — the caller then decides using
    retrieval results whether an answer is worth sending.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# Question heuristics: leading interrogatives, question mark, or
# an inverted Russian construction ("..., да?", "... верно?").
_QUESTION_MARK = "?"
_INTERROGATIVES = (
    "что ", "кто ", "как ", "где ", "куда ", "откуда ", "когда ", "почему ",
    "зачем ", "какой ", "какая ", "какое ", "какие ", "чей ", "сколько ",
    "можно ", "есть ли ", "а есть", "подскажи", "подскажите", "расскажи",
    "расскажите", "объясни", "объясните",
)
_TAIL_QUESTION = re.compile(r",\s*(да|нет|верно|правда|так)\s*\?*$", re.IGNORECASE)

# Social formulas. A greeting keeps its question mark ("привет всем, как дела?")
# but carries no query, so retrieval on it returns whatever happens to share a
# word with the archive. Treating these as questions is what makes the bot
# answer ordinary chatter, which the group rules forbid.
_SOCIAL_WORDS = {
    # Greetings and farewells.
    "привет", "приветик", "приветствую", "здравствуй", "здравствуйте",
    "здорово", "хай", "ку", "йо", "салют", "доброе", "добрый", "добрая",
    "доброй", "утро", "утречко", "день", "вечер", "ночи",
    "пока", "свидания", "увидимся", "споки", "бай",
    # Politeness.
    "спасибо", "спс", "пасиб", "благодарю", "пожалуйста", "извини", "извините",
    "сорри", "сорян",
    # "как дела" and friends.
    "дела", "делишки", "жизнь", "настроение", "успехи", "оно", "сам", "сама",
    # Address forms and filler that carry no query on their own.
    "всем", "народ", "ребята", "ребят", "коллеги", "друзья", "тут", "здесь",
    "живой", "кто", "как", "что", "чё", "че", "ты", "вы", "я", "мы", "он",
    "она", "они", "а", "и", "но", "же", "ну", "вот", "у", "нас", "вас",
}

# Matches a command with an optional @botname target: /faq@MyBot args
_COMMAND_RE = re.compile(r"^/([\w]+)(?:@([\w]+))?\s*(.*)$", re.DOTALL)


class Trigger(Enum):
    """Why a message was considered addressed to the bot."""

    NONE = "none"
    COMMAND = "command"       # /cmd — always handled by command routing
    MENTION = "mention"       # @bot or activation phrase
    REPLY = "reply"           # reply to a bot message
    QUESTION = "question"     # looks like a question (needs retrieval check)
    PRIVATE = "private"       # private chat — always answer

    def __bool__(self) -> bool:
        return self is not Trigger.NONE


@dataclass
class ParsedCommand:
    """A parsed slash command."""

    command: str        # normalized lowercase, no leading slash (e.g. "faq_add")
    args: str
    raw: str


@dataclass
class GateDecision:
    """Result of evaluating one incoming message."""

    trigger: Trigger
    parsed: ParsedCommand | None = None
    clean_text: str = ""      # text with the mention/command stripped

    @property
    def should_handle(self) -> bool:
        return bool(self.trigger)

    @property
    def is_command(self) -> bool:
        return self.trigger is Trigger.COMMAND

    @property
    def needs_retrieval_check(self) -> bool:
        """Questions only earn a reply if the knowledge base has something."""
        return self.trigger is Trigger.QUESTION


def parse_command(text: str) -> ParsedCommand | None:
    """Parse a leading /command, or return None if text is not a command."""
    match = _COMMAND_RE.match(text.strip())
    if not match:
        return None
    return ParsedCommand(
        command=match.group(1).lower(),
        args=match.group(3).strip(),
        raw=text.strip(),
    )


def is_command_for_bot(text: str, bot_username: str | None) -> bool:
    """True if a /command targets this bot (explicitly or implicitly)."""
    parsed = parse_command(text)
    if parsed is None:
        return False
    target = _COMMAND_RE.match(text.strip()).group(2)
    if target is None:
        return True  # plain "/faq" — assume ours in a private/group context
    return bool(bot_username) and target.lower() == bot_username.lower()


def is_smalltalk(text: str) -> bool:
    """
    True when the message is pure social chatter with no query in it.

    A message counts as smalltalk only if every word is a social one: that
    keeps "привет, как задеплоить?" a real question while "привет всем, как
    дела?" stays chatter.
    """
    words = re.findall(r"[\wёЁ]+", text.lower())
    if not words:
        return False
    return all(w in _SOCIAL_WORDS for w in words)


def looks_like_question(text: str) -> bool:
    """Heuristic question detection (Russian-first, English tolerant)."""
    stripped = text.strip()
    if not stripped:
        return False
    if is_smalltalk(stripped):
        # A greeting is not a question, whatever punctuation it ends with.
        return False
    lowered = stripped.lower()
    if _QUESTION_MARK in lowered:
        # Trailing question mark almost always means a question.
        if lowered.endswith(_QUESTION_MARK) or _TAIL_QUESTION.search(lowered):
            return True
    return lowered.startswith(_INTERROGATIVES)


def _strip_mention(text: str, bot_username: str | None, activation: str | None) -> tuple[str, bool]:
    """Remove mentions of the bot. Returns (clean_text, was_mentioned)."""
    mentioned = False
    if bot_username:
        pattern = re.compile(rf"@{re.escape(bot_username)}\b", re.IGNORECASE)
        if pattern.search(text):
            mentioned = True
            text = pattern.sub("", text)
    if activation:
        pattern = re.compile(rf"\b{re.escape(activation)}\b[,:!]?", re.IGNORECASE)
        if pattern.search(text):
            mentioned = True
            text = pattern.sub("", text)
    return text.strip(), mentioned


def decide(
    text: str,
    *,
    is_private: bool,
    bot_username: str | None = None,
    activation_phrase: str | None = None,
    is_reply_to_bot: bool = False,
) -> GateDecision:
    """Decide whether — and why — the bot should respond to this message."""
    if not text or not text.strip():
        return GateDecision(Trigger.NONE)

    # Private chats: answer everything (legacy behaviour, and the admin DM path).
    if is_private:
        parsed = parse_command(text)
        trigger = Trigger.COMMAND if parsed else Trigger.PRIVATE
        return GateDecision(trigger, parsed if trigger is Trigger.COMMAND else None,
                            text.strip())

    parsed = parse_command(text)
    if parsed and is_command_for_bot(text, bot_username):
        return GateDecision(Trigger.COMMAND, parsed, parsed.args)

    clean_text, mentioned = _strip_mention(text, bot_username, activation_phrase)

    if is_reply_to_bot:
        return GateDecision(Trigger.REPLY, None, clean_text)

    if mentioned:
        # A mention that is also a command was already routed above; here the
        # user wants an answer to whatever followed the mention.
        inner = parse_command(clean_text)
        if inner:
            return GateDecision(Trigger.COMMAND, inner, inner.args)
        return GateDecision(Trigger.MENTION, None, clean_text)

    if looks_like_question(clean_text):
        return GateDecision(Trigger.QUESTION, None, clean_text)

    return GateDecision(Trigger.NONE)
