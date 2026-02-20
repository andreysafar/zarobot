# Zero-Bot MVP Roadmap
## Пошаговая инструкция для task-manager MCP сервера

---

## 🎯 ЦЕЛЬ MVP
Создать базовую функциональную платформу для клонирования и настройки AI-ботов с простой экономикой.

## 📋 ЧТО ДОЛЖНО РАБОТАТЬ В MVP

### Основной функционал:
1. **Эхо-личность** - простой бот, отвечающий эхом на сообщения
2. **Веб-поиск тулз** - инструмент для поиска в интернете
3. **IAMother бот** - родительский бот для покупки личностей и тулзов
4. **UUID-паспорта** - уникальные идентификаторы для личностей и тулзов
5. **Базовая токеномика** - подписка в Stars, улучшения в IAM

### Техническое решение:
- **Контейнеризация**: каждый бот = отдельный Docker контейнер
- **Стек**: Django + Redis + MongoDB + Telethon
- **Клонирование**: быстрое создание копий zero-bot с кастомными модулями

---

## 🗑️ ЧТО УДАЛИТЬ (ЛИШНЕЕ ДЛЯ MVP)

### Файлы к удалению:
1. **Сложная документация**:
   - `ARCHITECTURE.md` - слишком детальная для MVP
   - `CORE_MECHANICS.md` - избыточная сложность
   - `DEVELOPMENT_ROADMAP.md` - заменяется этим файлом
   - `FINAL_REQUIREMENTS_SPECIFICATION.md` - дублирует PRD
   - `IMPLEMENTATION_CLARIFICATIONS.md` - не нужно в MVP
   - `TASK_DECOMPOSITION.md` - заменяется task-manager
   - `TOKENOMICS_ANALYSIS.md` - слишком сложно для MVP
   - `TOKENOMICS_AND_OWNERSHIP.md` - упрощается
   - `ZERO_BOT_CONSTRUCTOR.md` - не актуально
   
2. **Неиспользуемые сервисы из docker-compose.yml**:
   - `langflow` - пока не используется в MVP
   - `grafana` - мониторинг добавим позже

3. **Пустые директории интеграций**:
   - `zero_bot/integrations/langflow/` - пока не нужно
   - `zero_bot/integrations/ton/` - NFT добавим позже

4. **Избыточные Django приложения**:
   - `nft_manager` - NFT пока не используются
   - Оставить: `bot_factory`, `message_router`, `payments`, `tools_market`

---

## 🏗️ АРХИТЕКТУРА MVP

```
Zero-Bot MVP Platform
├── IAMother Bot (родительский)
│   ├── Регистрация пользователей
│   ├── Продажа личностей (UUID-паспорта)
│   ├── Продажа тулзов (UUID-паспорта)
│   └── Управление подписками Stars/IAM
├── Bot Factory
│   ├── Клонирование zero-bot контейнеров
│   ├── Настройка личностей + тулзов
│   └── Деплой готовых ботов
└── User Bots (клоны)
    ├── Echo Personality (базовая)
    ├── Web Search Tool (базовый)
    └── Пользовательские настройки
```

---

## 📝 ПОШАГОВАЯ ИНСТРУКЦИЯ ДЛЯ TASK-MANAGER

### ЭТАП 1: ОЧИСТКА ПРОЕКТА

**Задача 1.1: Удалить избыточную документацию**
```bash
# Удалить файлы
rm ARCHITECTURE.md CORE_MECHANICS.md DEVELOPMENT_ROADMAP.md
rm FINAL_REQUIREMENTS_SPECIFICATION.md IMPLEMENTATION_CLARIFICATIONS.md
rm TASK_DECOMPOSITION.md TOKENOMICS_ANALYSIS.md
rm TOKENOMICS_AND_OWNERSHIP.md ZERO_BOT_CONSTRUCTOR.md
```

**Задача 1.2: Упростить docker-compose.yml**
- Удалить сервисы: `langflow`, `grafana`
- Оставить: `django-core`, `mongodb`, `redis`
- Упростить volumes и networks

**Задача 1.3: Удалить пустые интеграции**
```bash
# Удалить пустые директории
rm -rf zero_bot/integrations/langflow/
rm -rf zero_bot/integrations/ton/
```

**Задача 1.4: Удалить NFT приложение**
```bash
rm -rf zero_bot/apps/nft_manager/
```

### ЭТАП 2: БАЗОВЫЕ МОДЕЛИ MVP

**Задача 2.1: Упростить модели в core/models.py**
- Убрать сложные NFT поля
- Оставить UUID-паспорта для личностей и тулзов
- Упростить экономическую модель

**Задача 2.2: Создать модель личностей**
```python
# zero_bot/personalities/models.py
class Personality(BaseModel):
    uuid_passport = fields.UUIDField(required=True, unique=True)
    name = fields.StringField(required=True)  # "echo", "advanced_echo"
    description = fields.StringField()
    price_iam = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
```

**Задача 2.3: Создать модель тулзов**
```python
# zero_bot/tools/models.py
class Tool(BaseModel):
    uuid_passport = fields.UUIDField(required=True, unique=True)
    name = fields.StringField(required=True)  # "web_search", "calculator"
    description = fields.StringField()
    price_iam = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
```

### ЭТАП 3: ПРОСТАЯ TELEGRAM ИНТЕГРАЦИЯ

**Задача 3.1: Создать базовый Telegram клиент с Telethon**
```python
# zero_bot/integrations/telegram/client.py
from telethon import TelegramClient, events

class ZeroBotTelegramClient:
    def __init__(self, api_id, api_hash, bot_token):
        self.client = TelegramClient('bot', api_id, api_hash)
        self.bot_token = bot_token
    
    async def start_bot(self):
        await self.client.start(bot_token=self.bot_token)
        self.client.add_event_handler(self.handle_message, events.NewMessage)
    
    async def handle_message(self, event):
        # Роутинг к личностям и тулзам
        pass
```

**Задача 3.2: Реализовать эхо-личность**
```python
# zero_bot/personalities/echo.py
class EchoPersonality:
    uuid_passport = "550e8400-e29b-41d4-a716-446655440000"
    
    async def process_message(self, message_text: str) -> str:
        return f"Эхо: {message_text}"
```

**Задача 3.3: Реализовать веб-поиск тулз**
```python
# zero_bot/tools/web_search.py
import aiohttp

class WebSearchTool:
    uuid_passport = "550e8400-e29b-41d4-a716-446655440001"
    
    async def search(self, query: str) -> str:
        # Простой поиск через публичное API
        pass
```

### ЭТАП 4: IAMother БОТ

**Задача 4.1: Создать IAMother как Django app**
```python
# zero_bot/apps/iamother/
├── models.py          # Модели для продажи личностей/тулзов
├── views.py           # API для покупки
├── telegram_bot.py    # Telegram интерфейс
└── payment_handler.py # Обработка Stars/IAM платежей
```

**Задача 4.2: Реализовать каталог личностей**
```python
# IAMother команды:
# /personalities - показать доступные личности
# /buy_personality <uuid> - купить личность
# /my_personalities - мои личности
```

**Задача 4.3: Реализовать каталог тулзов**
```python
# IAMother команды:
# /tools - показать доступные тулзы
# /buy_tool <uuid> - купить тулз
# /my_tools - мои тулзы
```

### ЭТАП 5: BOT FACTORY (КЛОНИРОВАНИЕ)

**Задача 5.1: Создать систему клонирования Docker контейнеров**
```python
# zero_bot/apps/bot_factory/cloner.py
import docker

class BotCloner:
    def __init__(self):
        self.docker_client = docker.from_env()
    
    async def clone_bot(self, user_id: str, personalities: list, tools: list):
        # 1. Создать новый контейнер из base zero-bot образа
        # 2. Настроить переменные окружения с UUID паспортами
        # 3. Запустить контейнер
        # 4. Вернуть bot_token и webhook_url
        pass
```

**Задача 5.2: Создать систему конфигурации ботов**
```python
# zero_bot/apps/bot_factory/configurator.py
class BotConfigurator:
    async def configure_bot(self, bot_id: str, config: dict):
        # Настройка личностей и тулзов для конкретного бота
        pass
```

### ЭТАП 6: БАЗОВАЯ ЭКОНОМИКА

**Задача 6.1: Создать систему Stars подписок**
```python
# zero_bot/apps/payments/stars.py
class StarsPaymentHandler:
    async def create_subscription(self, user_id: str, plan: str):
        # Создание подписки через Telegram Stars
        pass
    
    async def charge_for_usage(self, user_id: str, amount: int):
        # Списание Stars за использование функций
        pass
```

**Задача 6.2: Создать систему IAM токенов**
```python
# zero_bot/apps/payments/iam.py
class IAMTokenHandler:
    async def purchase_tokens(self, user_id: str, amount: int):
        # Покупка IAM токенов
        pass
    
    async def spend_tokens(self, user_id: str, amount: int, reason: str):
        # Трата IAM токенов на улучшения
        pass
```

### ЭТАП 7: РАЗВЕРТЫВАНИЕ MVP

**Задача 7.1: Создать MVP docker-compose.yml**
```yaml
version: '3.8'
services:
  django-core:
    build: .
    ports: ["8000:8000"]
    depends_on: [mongodb, redis]
  
  iamother-bot:
    build: .
    command: python manage.py run_iamother_bot
    depends_on: [mongodb, redis]
  
  mongodb:
    image: mongo:6.0
    
  redis:
    image: redis:7.0-alpine
```

**Задача 7.2: Создать базовый Dockerfile**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY zero_bot/ .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Задача 7.3: Настроить переменные окружения**
```bash
# .env.example
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
IAMOTHER_BOT_TOKEN=your_bot_token
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
```

---

## 🎯 ПРИОРИТЕТЫ ЗАДАЧ

### Критически важное (P0):
1. Очистка проекта от избыточности
2. Базовые модели (Bot, Personality, Tool)
3. Эхо-личность
4. IAMother бот с простым каталогом

### Важное (P1):
5. Веб-поиск тулз
6. Система клонирования ботов
7. Базовая экономика (Stars/IAM)

### Можно отложить (P2):
8. Продвинутые тулзы
9. Мониторинг и аналитика
10. UI для управления ботами

---

## 🧪 КРИТЕРИИ ГОТОВНОСТИ MVP

### Пользователь может:
1. ✅ Зарегистрироваться через IAMother бота
2. ✅ Купить эхо-личность за IAM токены
3. ✅ Купить веб-поиск тулз за IAM токены
4. ✅ Создать своего бота с купленными компонентами
5. ✅ Использовать бота (эхо + поиск)
6. ✅ Платить Stars за использование функций

### Платформа может:
1. ✅ Клонировать Docker контейнеры для новых ботов
2. ✅ Изолировать данные между ботами
3. ✅ Обрабатывать платежи Stars и IAM
4. ✅ Масштабироваться горизонтально

---

## 📈 ПЛАН ПОСЛЕ MVP

1. **Добавить NFT**: интеграция с TON для подтверждения владения
2. **Langflow интеграция**: продвинутые личности
3. **Marketplace**: торговля личностями/тулзами между пользователями
4. **Advanced AI**: интеграция с OpenAI, Anthropic
5. **Мониторинг**: возврат Grafana для аналитики

---

*Этот документ служит основной инструкцией для task-manager MCP сервера по приведению Zero-Bot проекта к состоянию MVP.* 