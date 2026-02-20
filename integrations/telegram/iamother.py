"""
Minimal Telegram bot stub for Zero-Bot platform.
Will be replaced with new dual-chain architecture.
"""

import os
import django
from telethon import TelegramClient, events
from dotenv import load_dotenv

# --- Django Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
# --- End Django Setup ---

# Load environment variables
load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('IAMOTHER_BOT_TOKEN')

# Initialize the Telegram Client
client = TelegramClient('zero_bot_session', API_ID, API_HASH)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Basic start command handler."""
    await event.reply("🤖 Zero Bot - dual-chain architecture coming soon!")

async def main():
    """Main function to start the bot."""
    if not BOT_TOKEN:
        print("BOT_TOKEN not found in environment variables")
        return
    
    await client.start(bot_token=BOT_TOKEN)
    print("Zero Bot started (minimal version)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main()) 