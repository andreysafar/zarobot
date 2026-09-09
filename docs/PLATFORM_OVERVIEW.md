# Zero Bot Platform — Полный обзор

> **Статус.** Документ описывает устройство платформы целиком, включая части,
> которые ещё не реализованы. Что именно работает сегодня, что заглушка и что
> не подключено — в [STATUS_REPORT.md](../STATUS_REPORT.md).

> Платформа для разворачивания Telegram-ботов с единым ядром.
> Каждый бот — это цифровой питомец (Tamagotchi) с NFT-паспортом, набором скиллов и владельцем.
> Инфраструктура: Telegram ↔ TON

---

## Общая архитектура

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Docker Host                                │
│                                                                       │
│  ┌───────────┐   ┌──────────┐   ┌────────┐   ┌──────────────┐      │
│  │ IA-Mother │   │ Core API │   │ Redis  │   │  Langflow    │      │
│  │ (Telethon)│──▶│ (FastAPI)│◀─▶│        │   │ (7860)       │      │
│  │           │   │          │   │        │   │              │      │
│  │ Docker    │   │ SQLite   │   │ State  │   │ Flow Builder │      │
│  │ Manager   │   │ 47 API   │   │ Cache  │   │              │      │
│  └─────┬─────┘   └────┬─────┘   └────────┘   └──────────────┘      │
│        │              │                                              │
│  ┌─────┴──────────────┴───────────────────────────────────────────┐  │
│  │              Bot Instances (zero-bot-{id})                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  │
│  │  │  Zero Bot│  │  Clone 1 │  │  Clone 2 │  ...               │  │
│  │  │ + LLM    │  │ + LLM    │  │ + LLM    │                    │  │
│  │  │ + Skills │  │ + Skills │  │ + Skills │                    │  │
│  │  └──────────┘  └──────────┘  └──────────┘                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────┐                                                         │
│  │ Скрепка  │  ← AI Admin: мониторинг, автодебаг, оркестрация        │
│  │ (agent)  │                                                         │
│  └──────────┘                                                         │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                   TON Blockchain                                 │  │
│  │  IAM-coin Jetton (EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8)  │  │
│  │  + Skill Registry via Core API                                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Сервисы

### 1. Core API (`services/core_api/`)

**Сервер приложения.** Единая точка входа для всех данных платформы.

- **Порт:** 8000
- **Технологии:** FastAPI + SQLAlchemy async + SQLite
- **Файлы:**
  - `main.py` (1166 строк) — 47 API-эндпоинтов
  - `database.py` (374 строки) — 12 моделей данных
  - `ton_client.py` (707 строк) — реальная интеграция с TON
  - `iam_coin.py` — off-chain учёт IAM-coin

**Модели данных:**

| Модель | Назначение |
|--------|-----------|
| `User` | Пользователи (telegram_id, username, is_premium) |
| `Balance` | Балансы (stars, ia_coins с Decimal precision) |
| `TonWallet` | TON кошельки (address, encrypted_private_key) |
| `Transaction` | Все транзакции (exchange, mint, burn, transfer, bot_purchase) |
| `Skill` | Навыки (name, description, price, pricing_model, revenue_split) |
| `SkillCategory` | Категории навыков |
| `BotPassport` | Паспорта ботов (owner, level, xp, nft_address, container_id) |
| `SkillInstallation` | Установленные навыки на ботов |
| `BugReport` | Баг-репорты (title, description, logs, ai_analysis) |
| `Donation` | Пожертвования разработчикам |
| `ErrorLog` | Логи ошибок от ботов |

**API-эндпоинты (47):**

| Группа | Эндпоинты |
|--------|-----------|
| Health | `GET /health` |
| Stats | `GET /api/v1/stats/` |
| Users | `GET/POST /api/v1/users/{id}/balance/`, `GET /api/v1/users/{id}/bots/` |
| Exchange | `GET /api/v1/exchange/rates/`, `POST /api/v1/exchange/`, `GET /api/v1/exchange/transactions/{id}` |
| Skills | `GET /api/v1/skills/skills/`, `GET /api/v1/skills/skills/{id}/`, `GET /api/v1/skills/skills/featured/`, `GET /api/v1/skills/categories/`, `POST /api/v1/skills/skills/{id}/install/` |
| Bot Passports | `GET /api/v1/bot-core/bot-passports/`, `GET /api/v1/bot-core/bot-passports/{id}/`, `POST /api/v1/bot-core/bot-passports/`, `PATCH /api/v1/bot-core/bot-passports/{id}/`, `GET /api/v1/bot-core/bot-passports/{id}/container/` |
| Marketplace | `GET /api/v1/marketplace/bots/`, `POST /api/v1/marketplace/skills/publish/`, `POST /api/v1/marketplace/skills/{id}/review/`, `GET /api/v1/marketplace/skills/search/`, `POST /api/v1/marketplace/bots/{id}/list/`, `POST /api/v1/marketplace/bots/{id}/buy/` |
| TON | `GET/POST /api/v1/ton/wallet/{id}`, `GET /api/v1/ton/balance/{address}`, `POST /api/v1/ton/transfer/`, `POST /api/v1/ton/nft/mint/`, `GET /api/v1/ton/nft/{id}`, `POST /api/v1/ton/nft/transfer/` |
| Feedback | `POST /api/v1/feedback/bug/`, `GET /api/v1/feedback/bugs/`, `PATCH /api/v1/feedback/bugs/{id}/` |
| Donations | `POST /api/v1/feedback/donate/`, `GET /api/v1/feedback/donations/sent/{id}`, `GET /api/v1/feedback/donations/received/{id}` |
| Error Logs | `POST /api/v1/feedback/error-logs/`, `GET /api/v1/feedback/error-logs/` |
| Скрепка | `GET /api/v1/skrepka/health/`, `POST /api/v1/skrepka/bug-analysis/` |
| IAM Coin | `GET /api/v1/iam-coin/info/`, `GET /api/v1/iam-coin/balance/{address}` |

---

### 2. IA-Mother (`services/ia-mother/`)

**Главный Telegram-бот платформы.** Точка входа для пользователей.

- **Технологии:** Telethon (async) + Docker SDK
- **Файлы:**
  - `ia_mother.py` — entry point + health server (порт 8002)
  - `bot.py` — Telegram client + handler registration
  - `config.py` — env vars + Redis + health app
  - `core_api.py` — HTTP-клиент к Core API (16 методов)
  - `docker_manager.py` — управление Docker-контейнерами ботов
  - `handlers/` — обработчики команд

**Меню IA-Mother:**

```
🤖 IA-Mother
├── 🏪 Маркетплейс
│   ├── 🤖 Боты (каталог + покупка)
│   ├── 🧠 Навыки (каталог + установка)
│   ├── 👑 Личности
│   ├── 🔥 Тренды
│   └── 🔍 Поиск
├── 💱 Обменник (Stars ↔ IA-Coins)
├── 🤖 Мои боты
│   ├── ➕ Создать бота (имя → токен → Docker)
│   ├── ⚙️ Управление (restart/stop/start/delete/logs)
│   └── 💰 Продать бота
├── 📊 Статистика
└── ℹ️ Помощь
```

**Поток создания бота:**
```
1. Пользователь → "➕ Создать бота"
2. Вводит имя бота
3. Вводит токен от @BotFather
4. Система:
   a. Core API: POST /bot-core/bot-passports/ → создать паспорт
   b. Docker: spawn_bot() → запустить контейнер с BOT_TOKEN
   c. Core API: PATCH → обновить container_id в паспорте
5. "Бот создан! Отправьте /start в Telegram"
```

**Docker Manager:**

| Метод | Описание |
|-------|----------|
| `spawn_bot()` | Создать и запустить контейнер бота |
| `stop_bot()` | Остановить (sleep mode) |
| `start_bot()` | Запустить после остановки |
| `restart_bot()` | Перезапуск |
| `destroy_bot()` | Удалить контейнер + volume |
| `get_bot_status()` | Статус контейнера |
| `list_active_bots()` | Список всех активных ботов |
| `get_bot_logs()` | Логи контейнера |
| `get_platform_stats()` | Статистика платформы |

**Характеристики контейнера бота:**
- Image: `zero-bot/bot-instance:latest`
- Network: `zero_bot_net`
- Memory: 256MB limit
- CPU: 0.5 core
- Restart: unless-stopped
- Volume: `bot_{id}_data:/data`

---

### 3. Zero Bot Instance (`services/bot-instance/`)

**Шаблон бота.** Это тот самый бот, который клонируется.

- **Технологии:** Telethon + LLM (OpenRouter/Anthropic/OpenAI) + Langflow
- **Файлы:**
  - `bot.py` (494 строки) — основной runtime
  - `handlers.py` — обработчики команд

**Компоненты Zero Bot:**

| Компонент | Назначение |
|-----------|-----------|
| `PersonalityLoader` | Загрузка личности из manifest + prompts |
| `BotState` | XP/level система с персистенцией |
| `ConversationManager` | История диалогов per-user (до 20 сообщений) |
| `LLMClient` | Multi-provider LLM с fallback chain |
| `CoreAPIClient` | Автоматическая отправка ошибок в Core API |

**Команды Zero Bot:**

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие от личности |
| `/stats` | Статистика: level, XP, messages |
| `/help` | Справка |
| `/reset` | Сброс истории диалога |
| `/bug` | Отправить баг-репорт |

**Pipeline обработки сообщения:**
```
User message
    ↓
Langflow (если LANGFLOW_API_URL + LANGFLOW_FLOW_ID)
    ↓ (fallback)
LLM Client (OpenRouter → Anthropic → OpenAI)
    ↓
Response to user
    ↓
Error? → Core API error-logs
```

**LLM fallback chain:**
1. OpenRouter (deepseek/deepseek-v4-flash-0731)
2. Anthropic (claude-3-5-haiku-20241022)
3. OpenAI (gpt-4o-mini)

---

### 4. Скрепка (`services/skrepka/`)

**AI Admin Agent.** Мониторит и управляет платформой.

- **Технологии:** Python + Docker SDK + httpx
- **Файлы:**
  - `agent.py` (311 строк) — основной агент

**Возможности:**

| Возможность | Описание |
|-------------|----------|
| Мониторинг контейнеров | Проверяет health каждые 5 минут |
| Авто-рестарт | Перезапускает unhealthy/exited боты |
| Анализ багов | Rule-based анализ открытых баг-репортов |
| Мониторинг ошибок | Группировка по ботам, алерты при ≥5 ошибках |
| Отчётность | Статистика в Core API |

**Цикл мониторинга (каждые 5 минут):**
```
1. Check containers health
   → unhealthy/exited + auto_restart → restart
2. Check open bug reports
   → без ai_analysis → analyze → submit
3. Check error logs
   → ≥5 errors per bot → report incident
4. Report stats
```

---

### 5. Redis

**State + Pub/Sub + Cache.**

- Состояние ботов
- Кэш реестра скиллов
- Pub/Sub для межсервисного общения

---

### 6. Langflow (внешний сервис)

**Визуальный конструктор flows.**

- Порт: 7860
- Используется для AI-ответов ботов
- Каждый бот может иметь свой flow

---

## Блокчейн-интеграция

### IAM-coin (TON Jetton)

```
Master:  EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql
Name:    IA Mother
Symbol:  IAM
Decimals: 2
Supply:  2,000,000,000 IAM
Mintable: true
Admin:   EQDLnFGoR9wegeRwhpd9bjyv_MKGXz8sizwC2OO4CZtjIq-s
TonScan: https://tonscan.org/jetton/EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql
```

**Операции:**
- `get_balance(address)` — запрос баланса через TonCenter API
- `transfer(from_wallet, to_wallet, amount)` — перевод (требует private key)
- `mint(admin_wallet, to_address, amount)` — эмиссия (только admin)

> **Что из этого работает.** Реально отправляется только `transfer`.
> `mint`, `burn` и операции с NFT возвращают отказ: отправка сообщений в сеть
> не реализована. Раньше они возвращали успех, ничего не сделав, — теперь нет.
>
> **Параметры расходятся с офчейн-реестром.** Ончейн-жетон объявлен с
> `decimals: 2` и предложением 2 млрд, а `IAMCoinService`, который сейчас
> ведёт балансы IAM, считает в 9 знаках с потолком 1 млрд. При переходе на
> ончейн эти параметры надо свести.

### Revenue Model (60/30/10)

При продаже скилла:
- 60% → создателю скилла
- 30% → платформе (platform_treasury)
- 10% → Telegram комиссия (резерв)

---

## Токеномика

### Заработок IAM-coin

| Способ | Описание |
|--------|----------|
| Создание скиллов | 60% от цены при каждой установке |
| Торговля ботами | Продажа развитых ботов на маркетплейсе |
| P2P обмен | Обмен IAM-coin между пользователями |

### Трата IAM-coin

| Способ | Описание |
|--------|----------|
| Установка скиллов | Покупка навыков для ботов |
| Покупка ботов | Покупка готовых ботов на маркетплейсе |
| Пожертвования | Финансирование разработчиков |

---

## Система обратной связи

### Баг-репорты

```
Пользователь → /bug → описывает проблему
    ↓
Core API: POST /feedback/bug/ → BugReport создан
    ↓
Скрепка: автоматический анализ → ai_analysis
    ↓
Скрепка: сообщение в чат отладки (если задан ADMIN_CHAT_ID)
```

Анализ у Скрепки сейчас правило-ориентированный: разбор логов по подстрокам
(`ConnectionError`, `KeyError`, `MemoryError`), а не вызов LLM.
Без `SKREPKA_BOT_TOKEN` и `ADMIN_CHAT_ID` уведомлений нет — отчёты остаются
в базе.

### Пожертвования

```
Пользователь → /donate 50 "На фикс бага"
    ↓
Core API: POST /feedback/donate/
    ↓
IAM-coin transfer: user → developer
    ↓
Опционально: привязка к bug_report_id
```

### Автоматический мониторинг

```
Zero Bot → любая ошибка → Core API error-logs
    ↓
Скрепка: группировка по ботам
    ↓
≥5 errors → incident report
```

---

## Маркетплейс скиллов

### Публикация через GitLab CI

```
Разработчик → skill repo → git tag v1.0.0
    ↓
GitLab CI Pipeline:
    1. Validate: JSON Schema + ruff + bandit
    2. Test: unit + sandbox (загрузка скилла)
    3. Build: tar.gz пакет
    4. Publish: Core API + TON регистрация (manual)
    ↓
Скилл появляется в маркетплейсе IA-Mother
```

### Установка скилла

```
Пользователь → "💾 Установить навык"
    ↓
Выбирает бота
    ↓
Core API: POST /skills/{id}/install/
    → Проверка баланса
    → Списание IAM-coin
    → Revenue split (60/30/10)
    → Запись установки
    ↓
Скилл активен в боте
```

### Модели ценообразования

| Модель | Revenue Split | Описа|-----------|---------------|--------|
| Free | — | Бесплатно |
| One-time | 60/30/10 | Разовая покупка |
| Subscription | 70/20/10 | Ежемесячная подписка |
| Freemium | 50/40/10 | Базовая бесплатно, премиум платно |
| Pay-per-use | 80/15/5 | Микротранзакции за вызов |

---

## CI/CD

### Скиллы (`ci/templates/skill.gitlab-ci.yml`)

```yaml
stages: [validate, test, build, publish]

validate:manifest  # JSON Schema
validate:lint       # ruff
validate:security   # bandit

test:unit           # pytest
test:sandbox        # загрузка скилла

build:package       # tar.gz

publish:registry    # Core API (on tag)
publish:ton         # TON registration (manual)
```

### Схемы валидации (`ci/schemas/`)

- `skill-manifest.schema.json` — схема манифеста скилла
- `personality-manifest.schema.json` — схема манифеста личности

---

## SDK (`sdk/zero_bot_sdk/`)

**Python SDK для создания скиллов и личностей.**

```python
from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse

class MySkill(BaseSkill):
    async def on_command(self, ctx: SkillContext, command: str, args: str) -> SkillResponse:
        if command == "/mycommand":
            return SkillResponse(text="Hello!")
        return SkillResponse.skip()
```

**CLI:**
```bash
zero-bot-sdk new skill my-skill     # scaffold скилл
zero-bot-sdk new personality my-pa  # scaffold личность
zero-bot-sdk test                   # тестирование
zero-bot-sdk chat                   # локальный чат
```

---

## Личности (`personalities/`)

### Ия (ia) — дефолтная личность

```
manifest.json:
  name: "ia"
  display_name: "Ия"
  ai_model:
    preferred: "google/gemini-3-pro-preview"
    fallback: "gpt-40"
    free_model: "gpt-4o-mini"
  behavior:
    response_style: "casual"
    emoji_usage: "moderate"
    formality: "medium"
    brevity: "high"
  features:
    user_profiling: true
    chat_summarization: true
    web_search: true
    image_analysis: true
```

**Промпты (7 файлов):**
- `system.txt` — основной системный промпт
- `system_free.txt` — для бесплатных пользователей
- `greeting.txt` — приветствие
- `fallback.txt` — ответ по умолчанию
- `context_agent.txt` — агент контекста чата
- `summary_agent.txt` — агент саммари чата
- `profile_agent.txt` — агент профиля пользователя

---

## Примеры (`examples/`)

### `examples/skill-weather/`

Полноценный пример скилла "Прогноз погоды":

```
skill-weather/
├── manifest.json          # Манифест (валидируется схемой)
├── handler.py             # WeatherSkill(BaseSkill)
├── requirements.txt       # httpx, zero-bot-sdk
├── tests/
│   └── test_handler.py    # 5 unit тестов
├── .gitlab-ci.yml         # CI pipeline
└── README.md              # Документация
```

---

## Запуск

### 1. Подготовка

```bash
cp .env.example .env
# Обязательно:
# TELEGRAM_API_ID=...
# TELEGRAM_API_HASH=...
# IA_MOTHER_BOT_TOKEN=...
# CORE_API_TOKEN=...        # openssl rand -hex 32; без него Core API не стартует
# Желательно:
# WALLET_ENCRYPTION_KEY=... # иначе операции с TON-кошельками отклоняются
# OWNER_ID=...              # создание ботов по умолчанию закрыто
# OPENROUTER_API_KEY=...
```

### 2. Сборка и запуск

```bash
docker compose up -d --build
```

### 3. Проверка

```bash
# Core API (порт слушает только localhost)
curl http://127.0.0.1:8000/health

# Остальные сервисы наружу не публикуются — смотреть логами:
docker compose logs -f ia-mother skrepka

# Langflow UI
open http://localhost:7860

# Redis
redis-cli -h localhost ping
```

### 4. Создание бота

1. Откройте IA-Mother в Telegram
2. Нажмите "🤖 Мои боты" → "➕ Создать бота"
3. Введите имя
4. Введите токен от @BotFather
5. Бот запускается в Docker-контейнере

---

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Cache | Redis 7 |
| Blockchain | TON (pytoniq, TonCenter API) |
| Telegram | Telethon (async) |
| AI | OpenRouter, Anthropic, OpenAI |
| Flows | Langflow |
| Containers | Docker, Docker Compose |
| CI/CD | GitLab CI |
| Monitoring | Скрепка (custom agent) |

---

## Строки кода

| Файл | Строк |
|------|-------|
| `services/core_api/main.py` | 1166 |
| `services/core_api/database.py` | 374 |
| `services/core_api/ton_client.py` | 707 |
| `services/bot-instance/bot.py` | 494 |
| `services/ia-mother/bot.py` | 215 |
| `services/ia-mother/docker_manager.py` | 262 |
| `services/ia-mother/core_api.py` | 280 |
| `services/skrepka/agent.py` | 311 |
| `docker-compose.yml` | 160 |
| **Итого** | **~4000** |

---

## TODO (следующие итерации)

- [ ] NFT Collection FunC контракт для паспортов ботов
- [ ] Реальная отправка TON транзакций (приватный ключ + gas management)
- [ ] WebApp для конструктора ботов (React/Vue)
- [ ] Шифрование приватных ключей в БД (Fernet/AES)
- [ ] Alembic миграции БД
- [ ] PostgreSQL для production
- [ ] Kubernetes для масштабирования
- [ ] Telegram Payments API для Stars
- [ ] Langflow flow builder API (программное создание flows)
- [ ] Скрепка: LLM-based анализ багов (не rule-based)
- [ ] Скрепка: аренда серверов (Hetzner API)
- [ ] Мониторинг: Prometheus + Grafana
