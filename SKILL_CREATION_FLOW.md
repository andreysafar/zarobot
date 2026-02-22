# Zero Bot - Полный процесс создания и регистрации навыков

## 🎯 Обзор процесса

Создание навыка в Zero Bot включает несколько этапов: от разработки в Core API до регистрации в Solana и появления в TON UI маркетплейсе через IA-Mother бота.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SKILL CREATION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│  1. Developer    │  2. Core API     │  3. Solana Core │  4. TON UI │
│     Creates      │     Stores       │     Registers   │    Shows   │
├─────────────────────────────────────────────────────────────────┤
│  • Code/API      │  • Django Model  │  • On-chain    │  • IA-Mother│
│  • Metadata      │  • Validation    │  • Registry PDA │  • Marketplace│
│  • Config        │  • Admin Review  │  • Payment Split│  • Install UI│
│  • Testing       │  • Status Track  │  • NFT Link     │  • Reviews  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Этап 1: Создание навыка разработчиком

### 1.1 Через Langflow WebApp (Рекомендуемый способ)

**Доступ:** Telegram WebApp через IA-Mother бота

```
Пользователь → IA-Mother → /start → 🏪 Маркетплейс → 🧠 Навыки → ➕ Создать навык
```

**Интерфейс создания:**
- 🎨 **Выбор категории** (Разработка, Языки, Анализ, Творчество, Утилиты)
- 📝 **Основная информация** (название, описание, версия)
- 💻 **Техническая реализация:**
  - API endpoint
  - Langflow узел
  - Webhook URL
  - Python модуль
- 🔧 **Конфигурация** (JSON схема параметров)
- 💰 **Ценообразование** (цена в IA-Coins или бесплатно)
- 🏷️ **Теги и метаданные**
- 🧪 **Тестирование** навыка

### 1.2 Через Core API напрямую

**Endpoint:** `POST /api/v1/skills/skills/`

```json
{
  "name": "Генерация кода Python",
  "description": "Автоматическая генерация кода на Python с использованием AI",
  "version": "1.0.0",
  "category": 1,
  "tags": ["python", "code", "ai"],
  "price_ia_coins": "25.00",
  "is_free": false,
  "execution_type": "api_call",
  "api_endpoint": "https://api.example.com/generate-code",
  "config_schema": {
    "language": {"type": "string", "default": "python"},
    "complexity": {"type": "string", "enum": ["simple", "medium", "complex"]}
  },
  "requirements": ["Python 3.8+"],
  "capabilities": ["code_generation", "syntax_checking"]
}
```

### 1.3 Через Django Admin

**Доступ:** `http://localhost:8000/admin/skills/skill/add/`

Полная форма создания навыка с всеми полями и валидацией.

---

## 🏢 Этап 2: Обработка в Core API (Django)

### 2.1 Создание записи в базе данных

**Модель:** `apps.skills.models.Skill`

```python
# Автоматически устанавливаемые поля при создании:
skill = Skill.objects.create(
    creator=request.user,           # Автоматически из токена
    status='draft',                 # Начальный статус
    is_public=False,               # Не публичный до модерации
    total_installations=0,         # Начальная статистика
    total_revenue=Decimal('0.00'),
    average_rating=Decimal('0.00')
)
```

### 2.2 Статусы навыка в Core API

- **`draft`** - Черновик, редактируется создателем
- **`pending_review`** - На модерации
- **`approved`** - Одобрен модератором
- **`rejected`** - Отклонен
- **`active`** - Активен в маркетплейсе
- **`deprecated`** - Устарел

### 2.3 Валидация и модерация

**Автоматическая валидация:**
- Проверка JSON схемы конфигурации
- Валидация API endpoints
- Проверка требований и зависимостей
- Анализ безопасности кода

**Ручная модерация:**
```python
# Через Django Admin или API
skill.status = 'approved'
skill.is_public = True
skill.published_at = timezone.now()
skill.save()
```

---

## ⛓️ Этап 3: Регистрация в Solana Core

### 3.1 Запуск регистрации

**Trigger:** Изменение статуса навыка на `approved`

**Endpoint Skill Registry Service:** `POST /register-skill`

```json
{
  "skill_id": "550e8400-e29b-41d4-a716-446655440001",
  "creator_solana_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
  "skill_metadata": {
    "skill_id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Генерация кода Python",
    "description": "...",
    "version": "1.0.0",
    "category": "development",
    "execution_type": "api_call",
    "handler_module": "skills.code_generator",
    "api_endpoint": "https://api.example.com/generate-code",
    "config_schema": {...},
    "requirements": ["Python 3.8+"],
    "capabilities": ["code_generation"]
  },
  "price_ia_coins": "25.00"
}
```

### 3.2 Создание Solana Registry PDA

**Программа:** Skill Registry Program (Anchor/Rust)

```rust
// Псевдокод Solana программы
#[program]
pub mod skill_registry {
    pub fn register_skill(
        ctx: Context<RegisterSkill>,
        skill_id: String,
        metadata: SkillMetadata,
        price: u64,
    ) -> Result<()> {
        let skill_registry = &mut ctx.accounts.skill_registry;
        
        skill_registry.skill_id = skill_id;
        skill_registry.creator = ctx.accounts.creator.key();
        skill_registry.metadata = metadata;
        skill_registry.price_ia_coins = price;
        skill_registry.total_installations = 0;
        skill_registry.is_active = true;
        skill_registry.created_at = Clock::get()?.unix_timestamp;
        
        Ok(())
    }
}
```

**PDA Seeds:** `["skill_registry", skill_id.as_bytes()]`

### 3.3 Обновление статуса в Core API

**Callback:** `POST /api/v1/skills/skills/{skill_id}/solana-registered/`

```json
{
  "registry_address": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
  "tx_hash": "5j7s8K9mN2pQ3rT4uV5wX6yZ7A8bC9dE0fG1hI2jK3lM4nO5pQ6rS7tU8vW9xY0z",
  "status": "active"
}
```

---

## 🎨 Этап 4: Синхронизация с TON UI

### 4.1 Создание записи для TON маркетплейса

**Redis Key:** `ton_marketplace_skill:{skill_id}`

```json
{
  "skill_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Генерация кода Python",
  "description": "Автоматическая генерация кода на Python с использованием AI",
  "price_ia_coins": "25.00",
  "creator": "@ai_developer",
  "category": "Разработка",
  "tags": ["python", "code", "ai"],
  "solana_registry_address": "8qbHbw2BbbTHBW1sbeqakYXVKRQM8Ne7pLK7m6CVfeR",
  "is_active": true,
  "sync_timestamp": "2024-02-20T15:30:00Z"
}
```

### 4.2 Уведомление IA-Mother бота

**Redis Pub/Sub:** Channel `ia_mother_updates`

```json
{
  "type": "new_skill",
  "skill_id": "550e8400-e29b-41d4-a716-446655440001",
  "data": {
    "name": "Генерация кода Python",
    "category": "Разработка",
    "price": "25.00",
    "creator": "@ai_developer"
  }
}
```

### 4.3 Появление в IA-Mother маркетплейсе

**Telegram Bot Flow:**
```
IA-Mother → /start → 🏪 Маркетплейс → 🧠 Навыки → [Новый навык появляется в списке]
```

---

## 💾 Процесс установки навыка

### 5.1 Пользователь выбирает навык в IA-Mother

```
🧠 Навыки → 🔍 [Навык] → 💾 Установить навык → 🤖 [Выбор бота] → ✅ Подтвердить
```

### 5.2 Обработка установки через Solana

**API Call:** `POST /install-skill` (Skill Registry Service)

```json
{
  "skill_id": "550e8400-e29b-41d4-a716-446655440001",
  "bot_nft_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
  "buyer_solana_address": "5KJh6NuyF8ZQyb7C3exDjWMBgAaL4A6JQsgiWY3StRhe"
}
```

### 5.3 Solana транзакции

**1. Оплата навыка (IA-coin SPL transfer):**
- 60% создателю навыка
- 30% протоколу Zero Bot
- 10% Telegram (за Stars)

**2. Обновление Bot PDA:**
- Добавление skill_id в список установленных навыков
- Обновление конфигурации бота

**3. Обновление Skill Registry:**
- Увеличение счетчика установок
- Добавление в статистику

### 5.4 Активация в боте

**Bot Instance получает уведомление:**
```json
{
  "type": "skill_installed",
  "skill_id": "550e8400-e29b-41d4-a716-446655440001",
  "config": {
    "language": "python",
    "complexity": "medium"
  }
}
```

---

## 📊 Мониторинг и аналитика

### 6.1 Метрики навыков

**Core API Dashboard:**
- Общее количество навыков
- Навыки по статусам
- Топ создателей
- Доходы по навыкам

**Solana Analytics:**
- On-chain установки
- Объем транзакций
- Распределение доходов

**TON UI Metrics:**
- Просмотры в маркетплейсе
- Конверсия установок
- Пользовательские рейтинги

### 6.2 Система рейтингов

**После установки пользователь может оценить:**

```
IA-Mother → Мои боты → ⚙️ [Бот] → 🧠 Навыки → ⭐ Оценить
```

**API:** `POST /api/v1/skills/skills/{skill_id}/rate/`

```json
{
  "rating": 5,
  "review": "Отличный навык! Генерирует качественный код."
}
```

---

## 🔄 Жизненный цикл навыка

### Статусы и переходы:

```
draft → pending_review → approved → active
  ↓           ↓             ↓
rejected    rejected    deprecated
```

### Автоматические действия:

- **При `approved`** → Запуск регистрации в Solana
- **При `active`** → Синхронизация с TON UI
- **При установке** → Обновление статистики
- **При оценке** → Пересчет рейтинга

---

## 🛠️ Техническая реализация

### Компоненты системы:

1. **Core API (Django)** - Основная логика и хранение
2. **Skill Registry Service (FastAPI)** - Solana интеграция
3. **IA-Mother Bot (Telethon)** - TON UI маркетплейс
4. **Bot Instances** - Выполнение навыков
5. **Langflow WebApp (Next.js)** - Интерфейс создания

### Коммуникация между сервисами:

- **HTTP API** - Синхронные запросы
- **Redis Pub/Sub** - Асинхронные уведомления
- **Webhook callbacks** - Обратная связь от Solana
- **Database triggers** - Автоматические действия

---

## 🎯 Готовность к демонстрации

### ✅ Что работает:
- Создание навыков через Core API
- Django Admin интерфейс
- IA-Mother маркетплейс UI
- Skill Registry Service (mock Solana)

### 🚧 Что требует доработки:
- Реальные Solana смарт-контракты
- Langflow WebApp интерфейс
- Платежная система IA-coins
- TON Wallet интеграция

### 🎪 Демо сценарий:

1. **Создание навыка** в Django Admin
2. **Модерация** и одобрение
3. **Просмотр в IA-Mother** маркетплейсе
4. **Установка на бота** (mock процесс)
5. **Статистика и аналитика**

**Результат:** Полнофункциональная система создания и управления навыками готова для MVP демонстрации! 🚀