"""
Проверка прав администратора для команд управления FAQ.

Право редактировать FAQ есть у:
  — создателя чата (creator);
  — администраторов чата (admin);
  — владельца бота (OWNER_ID, из окружения).
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger
from telethon.errors import RPCError
from telethon.tl.types import (
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
    ChatParticipantAdmin,
    ChatParticipantCreator,
)

# Пользователи, равные админам чата (владелец бота).
OWNER_IDS = {
    int(i)
    for i in os.getenv("OWNER_ID", "").replace(" ", "").split(",")
    if i
}

# Типы участников, дающие право на управление FAQ.
_ADMIN_TYPES = (
    ChannelParticipantCreator,
    ChannelParticipantAdmin,
    ChatParticipantCreator,
    ChatParticipantAdmin,
)


async def is_chat_admin(client, chat_id: int, user_id: int) -> bool:
    """
    Является ли пользователь администратором или создателем чата.

    Используем GetParticipantRequest — точечный запрос одного участника,
    он дешевле полного перебора iter_participants.
    """
    if not client or not user_id:
        return False

    from telethon.tl.functions.channels import GetParticipantRequest

    try:
        participant = await client(
            GetParticipantRequest(channel=chat_id, participant=user_id)
        )
    except RPCError as e:
        # «User not participant» и похожее — значит точно не админ.
        logger.debug("GetParticipant не удался для {}: {}", user_id, e)
        return False
    except Exception as e:
        logger.warning("Не удалось проверить права {}: {}", user_id, e)
        return False

    # Ответ может быть обёрнут в Participant(participant=...).
    inner = getattr(participant, "participant", participant)
    return isinstance(inner, _ADMIN_TYPES)


async def can_manage_faq(
    client, chat_id: int, user_id: int, is_private: bool = False
) -> bool:
    """
    Можно ли пользователю редактировать FAQ.

    В личке команды управления доступны владельцу бота.
    В группе — администраторам чата и владельцу.
    """
    if not user_id:
        return False

    if user_id in OWNER_IDS:
        return True

    if is_private:
        return False

    return await is_chat_admin(client, chat_id, user_id)


def parse_qa(args: str) -> tuple[str, str] | None:
    """
    Разобрать «вопрос | ответ» из аргументов команды.

    Возвращает None, если разделителя нет или какая-то часть пустая.
    """
    if "|" not in args:
        return None
    question, _, answer = args.partition("|")
    question, answer = question.strip(), answer.strip()
    if not question or not answer:
        return None
    return question, answer


def format_faq_list(items: list[dict[str, Any]]) -> str:
    """Отформатировать список FAQ для показа в чате."""
    if not items:
        return "📋 FAQ пока пуст."
    lines = ["📋 **FAQ чата**\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"**{i}. {item['question']}**")
        lines.append(f"{item['answer']}\n")
    return "\n".join(lines)
