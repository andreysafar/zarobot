"""
Bot Factory Service - Динамическое создание и управление ботами
Каждый бот запускается в отдельном Docker контейнере
"""

import asyncio
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

import docker
import httpx
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

# Configuration
CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
DOCKER_HOST = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
BOT_IMAGE_NAME = os.getenv("BOT_IMAGE_NAME", "zero-bot-instance")

# Initialize services
app = FastAPI(title="Bot Factory Service", version="1.0.0")
docker_client = docker.from_env()
redis_client = redis.from_url(REDIS_URL)

# Data models
class BotCreateRequest(BaseModel):
    bot_passport_id: str
    owner_ton_address: str
    personality_id: Optional[str] = None
    langflow_config: Optional[Dict] = None
    telegram_token: str
    resource_limits: Optional[Dict] = {
        "memory": "512m",
        "cpu_shares": 512
    }

class BotStatus(BaseModel):
    bot_id: str
    container_id: str
    status: str
    created_at: datetime
    last_heartbeat: Optional[datetime] = None
    resource_usage: Optional[Dict] = None

class BotManager:
    """Управление жизненным циклом ботов"""
    
    def __init__(self):
        self.active_bots: Dict[str, BotStatus] = {}
        self.load_active_bots()
    
    def load_active_bots(self):
        """Загрузка активных ботов из Redis"""
        try:
            bot_keys = redis_client.keys("bot:*")
            for key in bot_keys:
                bot_data = redis_client.get(key)
                if bot_data:
                    bot_status = BotStatus.model_validate_json(bot_data)
                    self.active_bots[bot_status.bot_id] = bot_status
            logger.info(f"Загружено {len(self.active_bots)} активных ботов")
        except Exception as e:
            logger.error(f"Ошибка загрузки ботов: {e}")
    
    async def create_bot(self, request: BotCreateRequest) -> BotStatus:
        """Создание нового бота в отдельном контейнере"""
        try:
            # Генерация уникального имени контейнера
            container_name = f"zero_bot_instance_{request.bot_passport_id}"
            
            # Проверка существования контейнера
            if self._container_exists(container_name):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Бот {request.bot_passport_id} уже существует"
                )
            
            # Подготовка конфигурации
            bot_config = await self._prepare_bot_config(request)
            
            # Создание Docker контейнера
            container = await self._create_container(
                container_name, 
                bot_config, 
                request.resource_limits
            )
            
            # Запуск контейнера
            container.start()
            
            # Создание записи о боте
            bot_status = BotStatus(
                bot_id=request.bot_passport_id,
                container_id=container.id,
                status="starting",
                created_at=datetime.utcnow()
            )
            
            # Сохранение в Redis и локальный кеш
            await self._save_bot_status(bot_status)
            self.active_bots[request.bot_passport_id] = bot_status
            
            # Уведомление Core API о создании бота
            await self._notify_core_api("bot_created", bot_status)
            
            logger.info(f"Создан бот {request.bot_passport_id} в контейнере {container.id}")
            return bot_status
            
        except Exception as e:
            logger.error(f"Ошибка создания бота {request.bot_passport_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def stop_bot(self, bot_id: str) -> bool:
        """Остановка бота"""
        try:
            if bot_id not in self.active_bots:
                raise HTTPException(status_code=404, detail="Бот не найден")
            
            bot_status = self.active_bots[bot_id]
            container = docker_client.containers.get(bot_status.container_id)
            
            # Graceful shutdown
            container.stop(timeout=30)
            container.remove()
            
            # Обновление статуса
            bot_status.status = "stopped"
            await self._save_bot_status(bot_status)
            
            # Удаление из активных ботов
            del self.active_bots[bot_id]
            redis_client.delete(f"bot:{bot_id}")
            
            # Уведомление Core API
            await self._notify_core_api("bot_stopped", bot_status)
            
            logger.info(f"Остановлен бот {bot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки бота {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def restart_bot(self, bot_id: str) -> BotStatus:
        """Перезапуск бота"""
        try:
            if bot_id not in self.active_bots:
                raise HTTPException(status_code=404, detail="Бот не найден")
            
            bot_status = self.active_bots[bot_id]
            container = docker_client.containers.get(bot_status.container_id)
            
            # Перезапуск контейнера
            container.restart(timeout=30)
            
            # Обновление статуса
            bot_status.status = "restarting"
            bot_status.last_heartbeat = datetime.utcnow()
            await self._save_bot_status(bot_status)
            
            logger.info(f"Перезапущен бот {bot_id}")
            return bot_status
            
        except Exception as e:
            logger.error(f"Ошибка перезапуска бота {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_bot_config(self, bot_id: str, config: Dict) -> BotStatus:
        """Обновление конфигурации бота"""
        try:
            if bot_id not in self.active_bots:
                raise HTTPException(status_code=404, detail="Бот не найден")
            
            # Сохранение новой конфигурации
            redis_client.set(f"bot_config:{bot_id}", json.dumps(config))
            
            # Уведомление бота о необходимости перезагрузки конфигурации
            redis_client.publish(f"bot_channel:{bot_id}", json.dumps({
                "type": "config_update",
                "config": config
            }))
            
            bot_status = self.active_bots[bot_id]
            logger.info(f"Обновлена конфигурация бота {bot_id}")
            return bot_status
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации бота {bot_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _container_exists(self, name: str) -> bool:
        """Проверка существования контейнера"""
        try:
            docker_client.containers.get(name)
            return True
        except docker.errors.NotFound:
            return False
    
    async def _prepare_bot_config(self, request: BotCreateRequest) -> Dict:
        """Подготовка конфигурации бота"""
        # Получение данных из Core API
        async with httpx.AsyncClient() as client:
            # Получение данных бота
            bot_response = await client.get(
                f"{CORE_API_URL}/api/v1/bot-core/bot-passports/{request.bot_passport_id}/"
            )
            bot_data = bot_response.json()
            
            # Получение личности (если указана)
            personality_data = None
            if request.personality_id:
                personality_response = await client.get(
                    f"{CORE_API_URL}/api/v1/personalities/{request.personality_id}/"
                )
                personality_data = personality_response.json()
        
        return {
            "bot_passport_id": request.bot_passport_id,
            "owner_ton_address": request.owner_ton_address,
            "telegram_token": request.telegram_token,
            "bot_data": bot_data,
            "personality_data": personality_data,
            "langflow_config": request.langflow_config or {},
            "core_api_url": CORE_API_URL,
            "redis_url": REDIS_URL,
            "bot_channel": f"bot_channel:{request.bot_passport_id}"
        }
    
    async def _create_container(self, name: str, config: Dict, limits: Dict) -> docker.models.containers.Container:
        """Создание Docker контейнера для бота"""
        
        # Environment variables для бота
        environment = {
            "BOT_CONFIG": json.dumps(config),
            "TELEGRAM_BOT_TOKEN": config["telegram_token"],
            "CORE_API_URL": config["core_api_url"],
            "REDIS_URL": config["redis_url"],
            "BOT_CHANNEL": config["bot_channel"],
            "BOT_PASSPORT_ID": config["bot_passport_id"]
        }
        
        # Ресурсные ограничения
        host_config = docker_client.api.create_host_config(
            mem_limit=limits.get("memory", "512m"),
            cpu_shares=limits.get("cpu_shares", 512),
            restart_policy={"Name": "unless-stopped"}
        )
        
        # Создание контейнера
        container = docker_client.containers.create(
            image=BOT_IMAGE_NAME,
            name=name,
            environment=environment,
            host_config=host_config,
            networks=["zero_bot_network"],
            labels={
                "zero_bot.type": "bot_instance",
                "zero_bot.bot_id": config["bot_passport_id"],
                "zero_bot.owner": config["owner_ton_address"]
            }
        )
        
        return container
    
    async def _save_bot_status(self, bot_status: BotStatus):
        """Сохранение статуса бота в Redis"""
        redis_client.set(
            f"bot:{bot_status.bot_id}", 
            bot_status.model_dump_json(),
            ex=86400  # 24 hours TTL
        )
    
    async def _notify_core_api(self, event_type: str, bot_status: BotStatus):
        """Уведомление Core API о событиях бота"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/bot-events/",
                    json={
                        "event_type": event_type,
                        "bot_id": bot_status.bot_id,
                        "container_id": bot_status.container_id,
                        "status": bot_status.status,
                        "timestamp": bot_status.created_at.isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка уведомления Core API: {e}")

# Глобальный менеджер ботов
bot_manager = BotManager()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_bots": len(bot_manager.active_bots),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/bots", response_model=BotStatus)
async def create_bot(request: BotCreateRequest, background_tasks: BackgroundTasks):
    """Создание нового бота"""
    return await bot_manager.create_bot(request)

@app.get("/bots", response_model=List[BotStatus])
async def list_bots():
    """Список всех активных ботов"""
    return list(bot_manager.active_bots.values())

@app.get("/bots/{bot_id}", response_model=BotStatus)
async def get_bot(bot_id: str):
    """Получение информации о боте"""
    if bot_id not in bot_manager.active_bots:
        raise HTTPException(status_code=404, detail="Бот не найден")
    return bot_manager.active_bots[bot_id]

@app.delete("/bots/{bot_id}")
async def stop_bot(bot_id: str):
    """Остановка бота"""
    success = await bot_manager.stop_bot(bot_id)
    return {"success": success}

@app.post("/bots/{bot_id}/restart", response_model=BotStatus)
async def restart_bot(bot_id: str):
    """Перезапуск бота"""
    return await bot_manager.restart_bot(bot_id)

@app.put("/bots/{bot_id}/config", response_model=BotStatus)
async def update_bot_config(bot_id: str, config: Dict):
    """Обновление конфигурации бота"""
    return await bot_manager.update_bot_config(bot_id, config)

@app.get("/stats")
async def get_stats():
    """Статистика Bot Factory"""
    containers = docker_client.containers.list(
        filters={"label": "zero_bot.type=bot_instance"}
    )
    
    return {
        "total_containers": len(containers),
        "active_bots": len(bot_manager.active_bots),
        "docker_info": docker_client.info(),
        "memory_usage": sum(
            container.stats(stream=False).get("memory_stats", {}).get("usage", 0)
            for container in containers
        )
    }

# Background tasks
async def monitor_bots():
    """Мониторинг состояния ботов"""
    while True:
        try:
            for bot_id, bot_status in bot_manager.active_bots.items():
                try:
                    container = docker_client.containers.get(bot_status.container_id)
                    
                    # Обновление статуса
                    if container.status != bot_status.status:
                        bot_status.status = container.status
                        await bot_manager._save_bot_status(bot_status)
                    
                    # Проверка heartbeat
                    heartbeat_key = f"heartbeat:{bot_id}"
                    if redis_client.exists(heartbeat_key):
                        bot_status.last_heartbeat = datetime.utcnow()
                        await bot_manager._save_bot_status(bot_status)
                    
                except docker.errors.NotFound:
                    # Контейнер не найден - удаляем из активных
                    logger.warning(f"Контейнер для бота {bot_id} не найден")
                    del bot_manager.active_bots[bot_id]
                    redis_client.delete(f"bot:{bot_id}")
                
        except Exception as e:
            logger.error(f"Ошибка мониторинга ботов: {e}")
        
        await asyncio.sleep(30)  # Проверка каждые 30 секунд

# Startup event
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Bot Factory Service запущен")
    
    # Запуск мониторинга в фоне
    asyncio.create_task(monitor_bots())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)