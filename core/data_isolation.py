"""
Data Isolation Utilities for Zero-Bot Platform.

This module provides functions and decorators to enforce strict data isolation
based on `bot_id` and user ownership, preventing data leakage between bots.
"""

import os
from functools import wraps
from django.http import JsonResponse
from django.conf import settings
from core.models import Bot

def get_bot_data_path(bot_id: str, user_id: str = None) -> str:
    """
    Constructs a standardized data path for a bot and optional user.
    Ensures that all bot-related data is stored in a unique, isolated directory.

    Args:
        bot_id: The unique identifier of the bot.
        user_id: The unique identifier of the user (optional).

    Returns:
        A string representing the isolated data path.
    """
    base_path = os.path.join(settings.DATA_DIR, 'bots', str(bot_id))
    if user_id:
        return os.path.join(base_path, 'users', str(user_id))
    return base_path

def ensure_bot_data_access(request, bot_id: str) -> bool:
    """
    Validates if the currently authenticated user has ownership rights for the given bot.
    This is a core function for enforcing data isolation at the API level.

    Args:
        request: The Django HTTP request object, containing user information.
        bot_id: The unique identifier of the bot being accessed.

    Returns:
        True if the user is the owner of the bot, False otherwise.
    """
    # In a real application, the user would be on request.user
    # For now, we assume a user object with a wallet_address attribute.
    # This check needs to be integrated with your actual authentication system.
    user_wallet = getattr(request.user, 'wallet_address', None)
    if not user_wallet:
        return False

    try:
        bot = Bot.objects.get(bot_id=bot_id)
        return bot.owner_wallet_address == user_wallet
    except Bot.DoesNotExist:
        return False

def bot_access_required(view_func):
    """
    A decorator for Django views that enforces bot ownership.
    It checks if the user making the request is the owner of the bot
    specified by `bot_id` in the URL.

    Usage:
        @bot_access_required
        def my_view(request, bot_id, *args, **kwargs):
            # ... view logic ...
    """
    @wraps(view_func)
    def _wrapped_view(request, bot_id: str, *args, **kwargs):
        if not ensure_bot_data_access(request, bot_id):
            return JsonResponse({'error': 'Forbidden: You do not have access to this bot.'}, status=403)
        return view_func(request, bot_id, *args, **kwargs)
    return _wrapped_view

def create_isolated_directory(path: str):
    """
    Safely creates a directory if it doesn't exist.

    Args:
        path: The directory path to create.
    """
    os.makedirs(path, exist_ok=True) 