"""
Skill Registry Service - Регистрация навыков в Solana blockchain
Обрабатывает регистрацию навыков в on-chain registry и синхронизацию с TON UI
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

import httpx
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

# Configuration
CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/3")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY")

# Initialize services
app = FastAPI(title="Skill Registry Service", version="1.0.0")
redis_client = redis.from_url(REDIS_URL)

# Data models
class SkillRegistrationRequest(BaseModel):
    skill_id: str
    creator_solana_address: str
    skill_metadata: Dict
    price_ia_coins: Decimal
    private_key: Optional[str] = None

class SkillInstallationRequest(BaseModel):
    skill_id: str
    bot_nft_address: str
    buyer_solana_address: str
    private_key: Optional[str] = None

class RegistryStatus(BaseModel):
    skill_id: str
    registry_address: Optional[str] = None
    tx_hash: Optional[str] = None
    status: str  # pending, processing, completed, failed
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

class SkillRegistryService:
    """Сервис регистрации навыков в Solana"""
    
    def __init__(self):
        self.pending_registrations: Dict[str, RegistryStatus] = {}
        self.load_pending_registrations()
    
    def load_pending_registrations(self):
        """Загрузка незавершенных регистраций из Redis"""
        try:
            keys = redis_client.keys("skill_registration:*")
            for key in keys:
                data = redis_client.get(key)
                if data:
                    registration = RegistryStatus.model_validate_json(data)
                    self.pending_registrations[registration.skill_id] = registration
            logger.info(f"Загружено {len(self.pending_registrations)} незавершенных регистраций")
        except Exception as e:
            logger.error(f"Ошибка загрузки регистраций: {e}")
    
    async def register_skill(self, request: SkillRegistrationRequest) -> RegistryStatus:
        """Регистрация навыка в Solana Registry"""
        try:
            # Создание записи о регистрации
            registration = RegistryStatus(
                skill_id=request.skill_id,
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Сохранение в Redis и локальный кеш
            await self._save_registration_status(registration)
            self.pending_registrations[request.skill_id] = registration
            
            # Запуск асинхронной обработки
            asyncio.create_task(self._process_skill_registration(request, registration))
            
            logger.info(f"Запущена регистрация навыка {request.skill_id}")
            return registration
            
        except Exception as e:
            logger.error(f"Ошибка запуска регистрации навыка {request.skill_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_skill_registration(
        self, 
        request: SkillRegistrationRequest, 
        registration: RegistryStatus
    ):
        """Асинхронная обработка регистрации навыка"""
        try:
            # Обновление статуса
            registration.status = "processing"
            registration.updated_at = datetime.utcnow()
            await self._save_registration_status(registration)
            
            # Импорт blockchain клиентов
            from blockchain.solana.registry import RegistryClient
            from blockchain.solana.client import SolanaClient
            
            # Инициализация клиентов
            solana_client = SolanaClient()
            registry_client = RegistryClient(
                solana_client=solana_client,
                registry_program_id="SkillRegistryProgramId123456789"  # TODO: Real program ID
            )
            
            # Регистрация в Solana
            result = await registry_client.register_skill(
                creator_address=request.creator_solana_address,
                skill_metadata=request.skill_metadata,
                price_ia_coin=request.price_ia_coins,
                private_key=request.private_key or SOLANA_PRIVATE_KEY
            )
            
            # Обновление статуса успешной регистрации
            registration.status = "completed"
            registration.registry_address = result.metadata.get("registry_address")
            registration.tx_hash = result.tx_hash
            registration.updated_at = datetime.utcnow()
            await self._save_registration_status(registration)
            
            # Уведомление Core API об успешной регистрации
            await self._notify_core_api_registration_complete(request.skill_id, registration)
            
            # Синхронизация с TON UI
            await self._sync_skill_to_ton_ui(request.skill_id, registration)
            
            logger.info(f"Навык {request.skill_id} успешно зарегистрирован в Solana")
            
        except Exception as e:
            # Обновление статуса ошибки
            registration.status = "failed"
            registration.error_message = str(e)
            registration.updated_at = datetime.utcnow()
            await self._save_registration_status(registration)
            
            # Уведомление Core API об ошибке
            await self._notify_core_api_registration_failed(request.skill_id, str(e))
            
            logger.error(f"Ошибка регистрации навыка {request.skill_id}: {e}")
    
    async def install_skill(self, request: SkillInstallationRequest) -> Dict:
        """Установка навыка на бота через Solana"""
        try:
            from blockchain.solana.registry import RegistryClient
            from blockchain.solana.client import SolanaClient
            
            solana_client = SolanaClient()
            registry_client = RegistryClient(
                solana_client=solana_client,
                registry_program_id="SkillRegistryProgramId123456789"
            )
            
            # Установка навыка
            result = await registry_client.install_skill(
                bot_nft_address=request.bot_nft_address,
                skill_id=request.skill_id,
                buyer_address=request.buyer_solana_address,
                private_key=request.private_key or SOLANA_PRIVATE_KEY
            )
            
            # Уведомление Core API об установке
            await self._notify_core_api_skill_installed(
                skill_id=request.skill_id,
                bot_nft_address=request.bot_nft_address,
                tx_hash=result.tx_hash,
                payment_tx=result.metadata.get("payment_tx")
            )
            
            return {
                "success": True,
                "tx_hash": result.tx_hash,
                "payment_tx": result.metadata.get("payment_tx"),
                "installation_address": result.metadata.get("installation_address")
            }
            
        except Exception as e:
            logger.error(f"Ошибка установки навыка {request.skill_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_skill_registry_data(self, skill_id: str) -> Optional[Dict]:
        """Получение данных навыка из Solana Registry"""
        try:
            from blockchain.solana.registry import RegistryClient
            from blockchain.solana.client import SolanaClient
            
            solana_client = SolanaClient()
            registry_client = RegistryClient(
                solana_client=solana_client,
                registry_program_id="SkillRegistryProgramId123456789"
            )
            
            return await registry_client.get_skill_data(skill_id)
            
        except Exception as e:
            logger.error(f"Ошибка получения данных навыка {skill_id}: {e}")
            return None
    
    async def _save_registration_status(self, registration: RegistryStatus):
        """Сохранение статуса регистрации в Redis"""
        redis_client.set(
            f"skill_registration:{registration.skill_id}",
            registration.model_dump_json(),
            ex=86400 * 7  # 7 days TTL
        )
    
    async def _notify_core_api_registration_complete(
        self, 
        skill_id: str, 
        registration: RegistryStatus
    ):
        """Уведомление Core API о завершении регистрации"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/skills/skills/{skill_id}/solana-registered/",
                    json={
                        "registry_address": registration.registry_address,
                        "tx_hash": registration.tx_hash,
                        "status": "active"
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка уведомления Core API о регистрации {skill_id}: {e}")
    
    async def _notify_core_api_registration_failed(self, skill_id: str, error: str):
        """Уведомление Core API об ошибке регистрации"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/skills/skills/{skill_id}/solana-failed/",
                    json={
                        "error": error,
                        "status": "rejected"
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка уведомления Core API об ошибке регистрации {skill_id}: {e}")
    
    async def _notify_core_api_skill_installed(
        self,
        skill_id: str,
        bot_nft_address: str,
        tx_hash: str,
        payment_tx: Optional[str] = None
    ):
        """Уведомление Core API об установке навыка"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/skills/installations/solana-completed/",
                    json={
                        "skill_id": skill_id,
                        "bot_nft_address": bot_nft_address,
                        "solana_install_tx": tx_hash,
                        "solana_payment_tx": payment_tx,
                        "status": "completed"
                    }
                )
        except Exception as e:
            logger.error(f"Ошибка уведомления Core API об установке навыка: {e}")
    
    async def _sync_skill_to_ton_ui(self, skill_id: str, registration: RegistryStatus):
        """Синхронизация навыка с TON UI маркетплейсом"""
        try:
            # Получение данных навыка из Core API
            async with httpx.AsyncClient() as client:
                skill_response = await client.get(
                    f"{CORE_API_URL}/api/v1/skills/skills/{skill_id}/"
                )
                
                if skill_response.status_code == 200:
                    skill_data = skill_response.json()
                    
                    # Создание записи в TON UI маркетплейсе
                    ton_marketplace_data = {
                        "skill_id": skill_id,
                        "name": skill_data["name"],
                        "description": skill_data["description"],
                        "price_ia_coins": str(skill_data["price_ia_coins"]),
                        "creator": skill_data["creator"]["username"],
                        "category": skill_data.get("category", {}).get("name", "General"),
                        "tags": skill_data.get("tags", []),
                        "solana_registry_address": registration.registry_address,
                        "is_active": True,
                        "sync_timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Сохранение в Redis для TON UI
                    redis_client.set(
                        f"ton_marketplace_skill:{skill_id}",
                        json.dumps(ton_marketplace_data),
                        ex=86400 * 30  # 30 days TTL
                    )
                    
                    # Уведомление IA-Mother о новом навыке
                    redis_client.publish(
                        "ia_mother_updates",
                        json.dumps({
                            "type": "new_skill",
                            "skill_id": skill_id,
                            "data": ton_marketplace_data
                        })
                    )
                    
                    logger.info(f"Навык {skill_id} синхронизирован с TON UI")
                    
        except Exception as e:
            logger.error(f"Ошибка синхронизации навыка {skill_id} с TON UI: {e}")

# Глобальный сервис регистрации
registry_service = SkillRegistryService()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "skill-registry",
        "pending_registrations": len(registry_service.pending_registrations),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/register-skill")
async def register_skill(request: SkillRegistrationRequest, background_tasks: BackgroundTasks):
    """Регистрация навыка в Solana Registry"""
    registration = await registry_service.register_skill(request)
    return registration

@app.post("/install-skill")
async def install_skill(request: SkillInstallationRequest):
    """Установка навыка на бота через Solana"""
    result = await registry_service.install_skill(request)
    return result

@app.get("/skill/{skill_id}/status")
async def get_registration_status(skill_id: str):
    """Получение статуса регистрации навыка"""
    if skill_id in registry_service.pending_registrations:
        return registry_service.pending_registrations[skill_id]
    
    # Проверка в Redis
    data = redis_client.get(f"skill_registration:{skill_id}")
    if data:
        return RegistryStatus.model_validate_json(data)
    
    raise HTTPException(status_code=404, detail="Registration not found")

@app.get("/skill/{skill_id}/registry-data")
async def get_skill_registry_data(skill_id: str):
    """Получение данных навыка из Solana Registry"""
    data = await registry_service.get_skill_registry_data(skill_id)
    if data:
        return data
    raise HTTPException(status_code=404, detail="Skill not found in registry")

@app.get("/marketplace/ton-sync")
async def get_ton_marketplace_skills():
    """Получение навыков, синхронизированных с TON UI"""
    try:
        keys = redis_client.keys("ton_marketplace_skill:*")
        skills = []
        
        for key in keys:
            data = redis_client.get(key)
            if data:
                skills.append(json.loads(data))
        
        return {
            "skills": skills,
            "count": len(skills),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения TON маркетплейс навыков: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_registry_stats():
    """Статистика Skill Registry"""
    try:
        # Подсчет регистраций по статусам
        status_counts = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        
        keys = redis_client.keys("skill_registration:*")
        for key in keys:
            data = redis_client.get(key)
            if data:
                registration = RegistryStatus.model_validate_json(data)
                status_counts[registration.status] = status_counts.get(registration.status, 0) + 1
        
        # TON маркетплейс навыки
        ton_skills_count = len(redis_client.keys("ton_marketplace_skill:*"))
        
        return {
            "total_registrations": len(keys),
            "status_breakdown": status_counts,
            "ton_marketplace_skills": ton_skills_count,
            "active_pending": len(registry_service.pending_registrations),
            "service_uptime": "calculated_uptime_here"
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks
async def monitor_registrations():
    """Мониторинг и переобработка зависших регистраций"""
    while True:
        try:
            current_time = datetime.utcnow()
            
            for skill_id, registration in registry_service.pending_registrations.items():
                # Переобработка зависших регистраций (старше 10 минут)
                if (registration.status == "processing" and 
                    (current_time - registration.updated_at).total_seconds() > 600):
                    
                    logger.warning(f"Переобработка зависшей регистрации {skill_id}")
                    registration.status = "pending"
                    registration.updated_at = current_time
                    await registry_service._save_registration_status(registration)
                    
                    # TODO: Перезапуск обработки
                    
        except Exception as e:
            logger.error(f"Ошибка мониторинга регистраций: {e}")
        
        await asyncio.sleep(300)  # Проверка каждые 5 минут

# Startup event
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Skill Registry Service запущен")
    
    # Запуск мониторинга в фоне
    asyncio.create_task(monitor_registrations())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)