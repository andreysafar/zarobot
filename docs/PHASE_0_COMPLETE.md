# Фаза 0 — Починка фундамента. Результат.

> **Исторический отчёт.** Фиксирует результат фазы на её дату и не обновляется.
> Актуальное состояние платформы — в [STATUS_REPORT.md](../STATUS_REPORT.md).

**Дата:** 2026-06-23
**Статус:** ✅ Завершено

---

## Что сделано

### 0.1 Критические баги исправлены

| Проблема | Статус | Что сделано |
|----------|--------|-------------|
| `Dockerfile.new` не существует | ✅ | docker-compose.yml исправлен, указан правильный Dockerfile |
| Двойной `_load_db()` в main.py | ✅ | Удалён JSON-подход, всё перешло на SQLAlchemy |
| `TELEGRAM_BOT_TOKEN` vs `IA_MOTHER_BOT_TOKEN` | ✅ | Переименовано в `IA_MOTHER_BOT_TOKEN` в config.py и bot.py |
| STUB DATA в core_api.py | ✅ | Убраны все заглушки, добавлен retry + CoreAPIError |

### 0.2 Миграция JSON → SQLite (SQLAlchemy async)

**Новый файл:** `services/core_api/database.py`

**Модели данных:**
- `User` — пользователи (telegram_id, username, is_premium)
- `Balance` — балансы (stars, ia_coins с Decimal precision)
- `TonWallet` — TON кошельки (address, encrypted_private_key)
- `Transaction` — все транзакции (exchange, mint, burn, transfer, skill_purchase, donation)
- `Skill` — навыки с pricing_model и revenue_split
- `SkillCategory` — категории навыков
- `BotPassport` — паспорта ботов (owner, level, xp, nft_address, container_id)
- `SkillInstallation` — установленные навыки на ботов
- `BugReport` — баг-репорты (с ai_analysis для Скрепки)
- `Donation` — пожертвования разработчикам
- `ErrorLog` — логи ошибок от ботов

**Подключение:** `sqlite+aiosqlite:///data/core_api/db.sqlite3`

### 0.3 Core API полностью переписан

**Новый файл:** `services/core_api/main.py` (v2.0.0)

**Эндпоинты (38 маршрутов):**

| Группа | Эндпоинты |
|--------|-----------|
| Health | `GET /health` |
| Stats | `GET /api/v1/stats/` |
| Users | `GET/POST /api/v1/users/{id}/balance/`, `GET /api/v1/users/{id}/bots/` |
| Exchange | `GET /api/v1/exchange/rates/`, `POST /api/v1/exchange/`, `GET /api/v1/exchange/transactions/{id}` |
| Skills | `GET /api/v1/skills/skills/`, `GET /api/v1/skills/skills/{id}/`, `GET /api/v1/skills/skills/featured/`, `GET /api/v1/skills/categories/`, `POST /api/v1/skills/skills/{id}/install/` |
| Bot Passports | `GET /api/v1/bot-core/bot-passports/`, `GET /api/v1/bot-core/bot-passports/{id}/`, `POST /api/v1/bot-core/bot-passports/` |
| Marketplace | `GET /api/v1/marketplace/bots/` |
| TON | `GET/POST /api/v1/ton/wallet/{id}`, `GET /api/v1/ton/balance/{address}`, `POST /api/v1/ton/transfer/`, `POST /api/v1/ton/nft/mint/`, `GET /api/v1/ton/nft/{id}`, `POST /api/v1/ton/nft/transfer/` |
| Feedback | `POST /api/v1/feedback/bug/`, `GET /api/v1/feedback/bugs/`, `PATCH /api/v1/feedback/bugs/{id}/` |
| Donations | `POST /api/v1/feedback/donate/`, `GET /api/v1/feedback/donations/sent/{id}`, `GET /api/v1/feedback/donations/received/{id}` |
| Error Logs | `POST /api/v1/feedback/error-logs/`, `GET /api/v1/feedback/error-logs/` |
| Скрепка | `GET /api/v1/skrepka/health/`, `POST /api/v1/skrepka/bug-analysis/` |

### 0.4 Зависимости обновлены

**`services/core_api/requirements.txt`:**
```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
python-multipart>=0.0.6
loguru>=0.7.0
httpx>=0.27.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0
alembic>=1.13.0
```

### 0.5 Docker Compose обновлён

- Убрана привязка к Solana
- Добавлены TON переменные окружения
- Добавлен сервис `skrepka` (профиль `skrepka`)
- Исправлены все Dockerfile пути
- Healthcheck для ia-mother на порту 8002

### 0.6 .env.example обновлён

- Убраны Solana переменные
- Добавлены: TON_API_KEY, TON_NETWORK, IAM_COIN_MASTER_ADDRESS, NFT_COLLECTION_ADDRESS, PLATFORM_TON_WALLET

---

## Что проверено

- [x] Все импорты работают без ошибок
- [x] 38 маршрутов зарегистрированы
- [x] БД создаётся, таблицы генерируются
- [x] Пользователь создаётся с балансом
- [x] Повторный запрос возвращает существующего пользователя (не дублирует)

---

## Что НЕ сделано (будет в следующих фазах)

- [ ] Seed-данные для навыков и категорий (были в старом main.py как hardcoded)
- [ ] Alembic миграции (пока auto-create, миграции понадобятся при изменении схемы)
- [ ] Интеграционные тесты
- [ ] TON интеграция (заглушки остаются в ton_client.py — Фаза 1)
- [ ] Docker Manager для клонирования ботов (Фаза 3)

---

## Следующий шаг

**Фаза 1: TON Jetton — реальная интеграция**
- Аудит существующего Jetton контракта
- Переписать ton_client.py на pytoniq
- Обменник: покупка IAM-coin за карту, P2P обмен, вывод на DEX
- Двойная запись: SQLite + TON
