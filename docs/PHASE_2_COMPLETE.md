# Фаза 2 — NFT-паспорта + Клонирование ботов. Результат.

> **Исторический отчёт.** Фиксирует результат фазы на её дату и не обновляется.
> Актуальное состояние платформы — в [STATUS_REPORT.md](../STATUS_REPORT.md).

**Дата:** 2026-06-24
**Статус:** ✅ Завершено

---

## Что сделано

### 2.1 Docker Manager (`services/ia-mother/docker_manager.py`)

Полноценный менеджер контейнеров для управления ботами:

| Метод | Описание |
|-------|----------|
| `spawn_bot()` | Создаёт и запускает контейнер бота |
| `stop_bot()` | Останавливает контейнер (sleep mode) |
| `start_bot()` | Запускает остановленный контейнер |
| `restart_bot()` | Перезапускает контейнер |
| `destroy_bot()` | Удаляет контейнер + volume |
| `get_bot_status()` | Статус контейнера |
| `list_active_bots()` | Список всех активных ботов |
| `get_bot_logs()` | Логи контейнера |
| `get_platform_stats()` | Статистика платформы |

**Характеристики контейнера:**
- Image: `zero-bot/bot-instance:latest`
- Network: `zero_bot_net`
- Memory limit: 256MB
- CPU: 0.5 core
- Restart policy: `unless-stopped`
- Labels: `app=zero-bot`, `bot-id`, `owner-id`, `bot-name`
- Volume: `bot_{id}_data:/data`

### 2.2 Поток создания бота обновлён (`handlers/my_bots.py`)

**Старый поток:** Кнопка → ссылка на WebApp (заглушка)

**Новый поток:**
```
1. Пользователь → "➕ Создать бота"
2. Бот запрашивает имя
3. Пользователь вводит имя
4. Бот запрашивает токен от @BotFather
5. Пользователь отправляет токен
6. Система:
   a. Core API: POST /api/v1/bot-core/bot-passports/ → create_bot_passport
   b. Docker: spawn_bot() → запуск контейнера с BOT_TOKEN, BOT_ID, OWNER_ID
   c. Core API: PATCH → обновляет container_id в паспорте
7. Пользователь получает: "Бот создан! Отправьте /start в Telegram"
```

### 2.3 Управление ботами

Новые команды:
- **⚙️ Управление** → панель управления ботом
- **🔄 Перезапустить** → restart контейнера
- **⏸️ Остановить** → stop (sleep mode, не удаляет данные)
- **▶️ Запустить** → start после остановки
- **🗑️ Удалить** → destroy с подтверждением
- **📋 Логи** → последние 50 строк логов контейнера

### 2.4 Core API обновлён

Новые эндпоинты:

| Метод | Путь | Описание |
|-------|------|----------|
| PATCH | `/api/v1/bot-core/bot-passports/{id}/` | Обновить container_id, nft_address, status |
| GET | `/api/v1/bot-core/bot-passports/{id}/container/` | Получить container_id |

### 2.5 Core API Client обновлён (`ia-mother/core_api.py`)

Новые методы:
- `create_passport(owner_id, owner_telegram, name, personality)` — создать паспорт бота
- `update_bot_container(bot_id, container_id)` — привязать контейнер
- `get_bot_status(bot_id)` — получить статус бота
- `submit_bug_report(user_id, title, description, bot_id, logs)` — отправить баг-репорт

### 2.6 База данных — новые данные

В таблице `bot_passports` теперь хранится:
- `container_id` — ID Docker-контейнера
- `nft_address` — адрес NFT-паспорта (когда будет задеплоена коллекция)

---

## Что проверено

- [x] Циклические импорты устранены (TYPE_CHECKING + lazy imports)
- [x] Docker SDK установлен и работает
- [x] BotContainerManager импортируется и имеет все методы (10 методов)
- [x] my_bots.py импортируется и имеет все обработчики (12 функций)
- [x] Core API: 40 маршрутов (было 38, добавлено PATCH и GET container)
- [x] Core API Client: 16 методов

---

## Что НЕ сделано (в следующих фазах)

- [ ] NFT Collection контракт нужно задеплоить (нужен FunC контракт)
- [ ] Реальный mint NFT при создании бота (требует NFT_COLLECTION_ADDRESS)
- [ ] Торговля ботами через NFT (маркетплейс)
- [ ] Автоматическое получение токена от BotFather
- [ ] Langflow flow для каждого бота (генерация flows)

---

## Итого: что работает сейчас

Запустить через `docker compose up -d`:

1. **Core API** (port 8000) — REST API для всего
2. **IA-Mother** — Telegram-бот (Telethon) с меню:
   - ➕ Создать бота (имя → токен → создаёт контейнер)
   - 📋 Мои боты (управление контейнерами)
   - 🏪 Маркетплейс (скиллы и личности)
   - 💱 обменник (IAM-coin операции)
   - 📊 Статистика
3. **Redis** — состояние + pub/sub
4. **Langflow** (port 7860) — визуальный редактор flows

---

## Следующий шаг

**Фаза 3: Обратная связь + Скрепка**
- Баг-репорты с логами
- Пожертвования разработчикам
- Скрепка (OpenClaw) для автоматического дебага
