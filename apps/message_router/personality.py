"""
Personality management for Zero-Bot platform.
Handles dynamic loading and processing of different bot personalities.
"""

import logging
from typing import Dict, Any, Optional
from core.models import UserSession, BotConfig

logger = logging.getLogger('zero_bot.personality')


class PersonalityManager:
    """
    Manages bot personalities and processes messages accordingly.
    Dynamically loads and dispatches to personality handlers.
    """

    def __init__(self):
        self._handlers = {
            'iya': self._handle_iya,
            'derValera': self._handle_derValera,
            'neJry': self._handle_neJry,
            'neJny': self._handle_neJny,
        }

    async def process_message(
        self,
        personality: str,
        message_data: Dict[str, Any],
        session: UserSession,
        bot_config: BotConfig
    ) -> Dict[str, Any]:
        """
        Process message using the specified personality handler.

        Args:
            personality: The personality to use (e.g., 'iya', 'derValera').
            message_data: Incoming message data from Telegram.
            session: The user's current session.
            bot_config: The configuration of the bot.

        Returns:
            A dictionary containing the response to be sent to the user.
        """
        handler = self._handlers.get(personality)
        if not handler:
            logger.error(f"No handler found for personality: {personality}")
            return {'text': 'Error: Personality not found.'}

        try:
            logger.info(f"Processing message with personality: {personality} for user {session.user_id}")
            response = await handler(message_data, session, bot_config)
            return response
        except Exception as e:
            logger.error(f"Error in {personality} handler: {e}")
            return {'text': 'An internal error occurred while processing your message.'}

    # --- Personality Handlers ---

    async def _handle_iya(
        self, message_data: Dict[str, Any], session: UserSession, bot_config: BotConfig
    ) -> Dict[str, Any]:
        """Handler for the 'iya' personality (default AI)."""
        user_name = session.first_name or "User"
        message_text = message_data.get('text', '')
        # In a real implementation, this would call Langflow or another AI service
        return {
            'text': f"Привет, {user_name}! Я - Ия, стандартный AI. Вы написали: '{message_text}'"
        }

    async def _handle_derValera(
        self, message_data: Dict[str, Any], session: UserSession, bot_config: BotConfig
    ) -> Dict[str, Any]:
        """Handler for the 'derValera' personality."""
        user_name = session.first_name or "User"
        message_text = message_data.get('text', '')
        return {
            'text': f"Здарова, {user_name}. Валера на связи. Ты тут накалякал: '{message_text}'"
        }

    async def _handle_neJry(
        self, message_data: Dict[str, Any], session: UserSession, bot_config: BotConfig
    ) -> Dict[str, Any]:
        """Handler for the 'neJry' personality."""
        user_name = session.first_name or "User"
        message_text = message_data.get('text', '')
        return {
            'text': f"Доброго времени суток, {user_name}. Это neJry. Ваше сообщение: '{message_text}'"
        }

    async def _handle_neJny(
        self, message_data: Dict[str, Any], session: UserSession, bot_config: BotConfig
    ) -> Dict[str, Any]:
        """Handler for the 'neJny' personality."""
        user_name = session.first_name or "User"
        message_text = message_data.get('text', '')
        return {
            'text': f"Приветики, {user_name}! neJny слушает. Ты написал(а): '{message_text}'"
        } 