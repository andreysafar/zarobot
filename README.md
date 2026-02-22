# Zero Bot - Масштабируемая платформа персональных AI ботов

🤖 **Революционная платформа для создания и управления персональными AI ботами с dual-chain экономикой**

## 🌟 Особенности

- 🐳 **Каждый бот в отдельном Docker контейнере** - Полная изоляция и масштабируемость
- 🎛️ **Langflow как Telegram WebApp** - Визуальное управление промптами и логикой
- 🔐 **TON Wallet аутентификация** - Безопасный вход через TON Connect
- 🪙 **Dual-chain экономика** - TON Jetton (UX) + Solana SPL (логика)
- 🏪 **IA-Mother маркетплейс** - Покупка/продажа ботов и навыков + обменник Stars ↔ IA-Coins
- 🎮 **Tamagotchi механики** - Боты растут и развиваются со временем
- 🧠 **Динамические личности** - Система личностей с рейтингами и категориями

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                    │
├─────────────────────────────────────────────────────────────┤
│  Core API (Django)     │  Redis Cluster  │  PostgreSQL     │
├─────────────────────────────────────────────────────────────┤
│  Bot Factory Service   │  Message Queue  │  File Storage   │
├─────────────────────────────────────────────────────────────┤
│  Bot-001 Container     │  Bot-002        │  Bot-003        │
├─────────────────────────────────────────────────────────────┤
│  IA-Mother Bot         │  Langflow App   │  TON Bridge     │
├─────────────────────────────────────────────────────────────┤
│  Monitoring Stack      │  Load Balancer  │  Backup Service │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Требования

### Системные зависимости:
- Docker & Docker Compose
- Python 3.12+
- Node.js 18+
- Git

### API ключи:
- `ANTHROPIC_API_KEY` - Для AI функций (обязательно)
- `TELEGRAM_API_ID` & `TELEGRAM_API_HASH` - Для Telegram интеграции
- `TON_API_KEY` - Для TON блокчейн интеграции (опционально)
- Telegram Bot Token для IA-Mother бота

## ⚡ Быстрый запуск

### 1. Клонирование и настройка:
```bash
git clone <repository>
cd Zero_bot

# Копирование переменных окружения
cp .env.example .env
# Отредактируйте .env файл с вашими API ключами
```

### 2. Запуск базового MVP:
```bash
# Запуск основных сервисов
docker-compose up -d postgres redis core-api

# Применение миграций
docker-compose exec core-api python manage.py migrate

# Создание суперпользователя
docker-compose exec core-api python manage.py createsuperuser

# Проверка работоспособности
curl http://localhost:8000/health/
```

### 3. Запуск полной масштабируемой системы:
```bash
# Запуск всех сервисов
docker-compose -f docker-compose.scalable.yml up -d

# Проверка статуса всех сервисов
docker-compose -f docker-compose.scalable.yml ps
```

## 🔧 Конфигурация

Основные переменные окружения в `.env`:

```bash
# Core API
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:pass@postgres:5432/zero_bot
REDIS_URL=redis://:password@redis:6379/0

# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
IA_MOTHER_BOT_TOKEN=your_bot_token

# AI Services
ANTHROPIC_API_KEY=your_anthropic_key

# Blockchain
TON_API_KEY=your_ton_key
SOLANA_RPC_URL=https://api.devnet.solana.com

# WebApp
WEBAPP_URL=https://your-domain.com
```

## 🧪 Тестирование

### Автоматические тесты:
```bash
# Unit тесты Core API
docker-compose exec core-api python manage.py test

# Тесты личностей
docker-compose exec core-api python manage.py test apps.personalities

# API тесты
docker-compose exec core-api python manage.py test --pattern="*api*"
```

### Ручное тестирование:

**Core API:**
```bash
# Создание личности
curl -X POST http://localhost:8000/api/v1/personalities/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Personality", "description": "Test", "system_prompt": "You are helpful"}'

# Список ботов
curl http://localhost:8000/api/v1/bot-core/bot-passports/
```

**Bot Factory:**
```bash
# Проверка статуса
curl http://localhost:8001/health

# Создание тестового бота
curl -X POST http://localhost:8001/bots \
  -H "Content-Type: application/json" \
  -d '{"bot_passport_id": "test_bot", "owner_ton_address": "test", "telegram_token": "test"}'
```

## 📊 Статус MVP

### ✅ Production Ready:
- **Core API** - Django REST с полным функционалом
- **Personalities System** - Динамические личности
- **Bot Models** - NFT Passport, XP система
- **Database** - PostgreSQL с миграциями
- **Docker** - Масштабируемая архитектура

### 🚧 Functional Mockups:
- **Bot Factory** - Создание ботов в контейнерах
- **IA-Mother Bot** - Маркетплейс + обменник
- **Langflow WebApp** - Визуальный редактор
- **TON Auth** - Аутентификация через кошелек

### ❌ Требует доработки:
- Реальные смарт-контракты
- Production безопасность
- Мониторинг и логирование
- CI/CD pipeline

## 🚀 Компоненты системы

### 🏢 Core API (Django REST)
- **Статус**: ✅ Production Ready
- **Функции**: Управление ботами, личностями, пользователями
- **Endpoints**: `/api/v1/bot-core/`, `/api/v1/personalities/`
- **База данных**: PostgreSQL с полными миграциями
- **Админка**: Django Admin с кастомными интерфейсами

### 🏭 Bot Factory (FastAPI)
- **Статус**: 🚧 Functional Mock
- **Функции**: Динамическое создание ботов в Docker контейнерах
- **API**: `/bots`, `/stats`, управление жизненным циклом
- **Масштабирование**: Автоматическое создание/удаление контейнеров

### 🤖 Individual Bot Instances
- **Статус**: 🚧 Template Ready
- **Функции**: Telegram боты с Langflow интеграцией
- **Изоляция**: Каждый бот в отдельном контейнере
- **Мониторинг**: Health checks и heartbeat система

### 👑 IA-Mother Bot (Маркетплейс)
- **Статус**: 🚧 Demo Ready
- **Функции**: Каталог ботов/навыков + обменник Stars ↔ IA-Coins
- **UI**: Telegram бот с красивым интерфейсом
- **Интеграция**: WebApp для создания ботов

### 🎛️ Langflow WebApp
- **Статус**: 🚧 Structure Ready
- **Функции**: Визуальный редактор промптов и логики
- **Технологии**: Next.js, React Flow, TON Connect
- **Интеграция**: Telegram WebApp с TON Wallet auth

## 📚 API Documentation

### Core API Endpoints:

**Bot Management:**
```
GET    /api/v1/bot-core/bot-passports/           # Список ботов
POST   /api/v1/bot-core/bot-passports/           # Создание бота
GET    /api/v1/bot-core/bot-passports/{id}/      # Детали бота
PUT    /api/v1/bot-core/bot-passports/{id}/      # Обновление
POST   /api/v1/bot-core/bot-passports/{id}/add_experience/  # XP
```

**Personalities:**
```
GET    /api/v1/personalities/                    # Каталог личностей
POST   /api/v1/personalities/                    # Создание
POST   /api/v1/personalities/{id}/install/      # Установка
POST   /api/v1/personalities/{id}/rate/         # Рейтинг
POST   /api/v1/personalities/search/            # Поиск
```

**Bot Factory:**
```
GET    /bots                     # Активные боты
POST   /bots                     # Создание бота
DELETE /bots/{id}                # Остановка
POST   /bots/{id}/restart        # Перезапуск
PUT    /bots/{id}/config         # Обновление конфигурации
```

## 🔗 Полезные ссылки

- 📖 **[Полная документация MVP](./MVP_DOCUMENTATION.md)** - Детальное описание всех компонентов
- 🏗️ **[Архитектура масштабируемости](./ARCHITECTURE_SCALABLE.md)** - Техническая архитектура
- 🐳 **[Docker Compose конфигурации](./docker-compose.scalable.yml)** - Полная инфраструктура
- ⚙️ **[Переменные окружения](./.env.example)** - Конфигурация системы

## 🤝 Участие в разработке

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- **TON Blockchain** - За инновационную блокчейн платформу
- **Solana** - За быструю и масштабируемую инфраструктуру
- **Langflow** - За визуальный подход к AI workflows
- **Django & FastAPI** - За мощные веб-фреймворки
- **Docker** - За контейнеризацию и масштабируемость

---

**Zero Bot - Будущее персональных AI ботов уже здесь! 🚀**
