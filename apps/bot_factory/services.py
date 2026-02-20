import docker
import uuid
from .models import Bot
from django.conf import settings
from typing import Optional

class BotFactoryService:
    """
    A service to manage the lifecycle of bot containers.
    """
    def __init__(self):
        """
        Initializes the Docker client.
        """
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            # Handle cases where Docker is not running or not configured correctly
            self.client = None
            print(f"Error initializing Docker client: {e}")

    def ping_docker(self) -> bool:
        """
        Pings the Docker daemon to check for a connection.

        Returns:
            True if the connection is successful, False otherwise.
        """
        if not self.client:
            return False
        try:
            return self.client.ping()
        except docker.errors.APIError as e:
            print(f"Error pinging Docker daemon: {e}")
            return False

    def generate_telegram_token(self, bot_name: str) -> str:
        """
        Generates a fake Telegram bot token for development purposes.

        Args:
            bot_name: The name of the bot, used for generating a predictable fake token.

        Returns:
            A fake Telegram bot token string.
        """
        # In a real application, this would involve a complex interaction with BotFather.
        # For now, we'll generate a predictable, fake token.
        fake_id = abs(hash(bot_name)) % (10**9)
        random_part = uuid.uuid4().hex[:6]
        return f"{fake_id}:FAKE_TOKEN_{random_part}"

    def save_bot_instance(self, owner_id: int, token: str, container_id: str, personality_uuid: str) -> Optional[Bot]:
        """
        Saves a new bot instance to the database.

        Args:
            owner_id: The ID of the user who owns the bot.
            token: The bot's Telegram token.
            container_id: The ID of the Docker container running the bot.
            personality_uuid: The UUID of the personality assigned to the bot.

        Returns:
            The created Bot instance, or None if an error occurred.
        """
        try:
            owner = settings.AUTH_USER_MODEL.objects.get(id=owner_id)
            bot = Bot.objects.create(
                owner=owner,
                token=token,
                container_id=container_id,
                personality_uuid=personality_uuid
            )
            return bot
        except settings.AUTH_USER_MODEL.DoesNotExist:
            print(f"User with id {owner_id} not found.")
            return None
        except Exception as e:
            print(f"Error saving bot instance: {e}")
            return None 