"""
Bot Core Django app configuration.
"""

from django.apps import AppConfig


class BotCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bot_core'
    verbose_name = 'Bot Core'
    
    def ready(self):
        """Initialize app when Django starts."""
        # Import signal handlers if needed
        pass