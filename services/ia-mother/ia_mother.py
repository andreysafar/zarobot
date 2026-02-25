"""
IA-Mother Bot - Маркетплейс ботов и навыков + Обменник Stars ↔ IA-Coins

Entry point: health server + Telegram bot.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Allow running as script: python ia_mother.py (Docker CMD)
if __name__ == "__main__":
    _root = Path(__file__).resolve().parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from loguru import logger

import config
from bot import IAMotherBot

# Attach health routes to shared app
if config.health_app is not None:

    @config.health_app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "ia-mother",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @config.health_app.get("/stats")
    async def get_health_stats():
        return {
            "service": "ia-mother",
            "uptime": "calculated_uptime",
            "active_users": "stored_count",
            "exchange_volume": "daily_volume",
        }


async def main():
    bot = IAMotherBot()
    try:
        await bot.start()
        if config.health_app is not None:
            import uvicorn
            server_config = uvicorn.Config(
                config.health_app, host="0.0.0.0", port=8002, log_level="info"
            )
            server = uvicorn.Server(server_config)
            asyncio.create_task(server.serve())
        await bot.client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка IA-Mother: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
