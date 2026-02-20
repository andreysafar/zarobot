import os
import django
from telethon import TelegramClient, events
from dotenv import load_dotenv

# --- Django Setup ---
# This block is crucial for running Telethon within the Django context
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
# --- End Django Setup ---

from core.models import User

# Load environment variables from .env file
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('IAMOTHER_BOT_TOKEN')

# Initialize the Telegram Client
# The session file will be created in the same directory as this script
client = TelegramClient('iamother_bot_session', API_ID, API_HASH)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handles the /start command."""
    sender = await event.get_sender()
    telegram_id = sender.id
    username = sender.username

    # Check if the user already exists in the database
    user_exists = await User.objects.filter(telegram_id=telegram_id).aexists()

    if user_exists:
        await event.reply(f"Welcome back, {username}!")
    else:
        # Create a new user instance
        new_user = await User.objects.acreate(
            telegram_id=telegram_id,
            username=username,
            iam_balance=0.0  # Initial balance
        )
        await event.reply(f"Hello, {username}! You have been successfully registered.")
        # Further logic for sending a welcome message will be added in the next task.

async def main():
    """Main function to start the bot."""
    # Start the bot using the bot token
    await client.start(bot_token=BOT_TOKEN)
    print("IAMother Bot has started successfully.")
    # Keep the client running
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main()) 