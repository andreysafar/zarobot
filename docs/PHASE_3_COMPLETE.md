# Фаза 3: Zero Bot — Живой бот + Обратная связь. Результат.

> **Исторический отчёт.** Фиксирует результат фазы на её дату и не обновляется.
> Актуальное состояние платформы — в [STATUS_REPORT.md](../STATUS_REPORT.md).

**Дата:** 2026-06-24
**Статус:** ✅ Завершено

---

## Что сделано

### 3.1 Zero Bot полностью переписан (`services/bot-instance/bot.py`)

**Было:** Telethon → PersonalityLoader → Langflow (если есть) → заглушка
**Стало:** Полноценный AI-бот с LLM, диалогами, автоматическим мониторингом

**Новые компоненты:**

| Компонент | Назначение |
|-----------|-----------|
| `LLMClient` | Multi-provider LLM: OpenRouter → Anthropic → OpenAI |
| `ConversationManager` | История диалогов per-user (JSON файл) |
| `CoreAPIClient` | Автоматическая отправка ошибок в Core API |
| `BotState` | XP/level система с персистенцией |
| `PersonalityLoader` | Загрузка личности из manifest + prompts |

**LLM приоритет:**
1. OpenRouter (google/gemini-2.0-flash-001 по умолчанию)
2. Anthropic (claude-3-5-haiku-20241022)
3. OpenAI (gpt-4o-mini)

**Pipeline обработки сообщения:**
```
User message → Langflow (если настроен) → LLM (fallback) → Response
                ↓ (ошибка)                     ↓ (ошибка)
         Core API error log              Core API error log
```

### 3.2 Новые команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие от личности |
| `/stats` | Статистика: level, XP, messages |
| `/help` | Справка по командам |
| `/reset` | Сброс истории диалога |
| `/bug` | Отправить баг-репорт |

### 3.3 Автоматический мониторинг ошибок

Бот автоматически отправляет в Core API:
- **Langflow errors** — когда flow недоступен или вернул ошибку
- **LLM errors** — когда все провайдеры недоступны
- **Message processing errors** — любые исключения в обработке

Payload:
```json
{
  "bot_id": "zero-bot",
  "user_id": 123456,
  "error_type": "llm_error",
  "message": "Connection timeout",
  "traceback": "...",
  "context": {"model": "google/gemini-2.0-flash-001"}
}
```

### 3.4 Обратная связь с разработчиками

**Баг-репорты:**
- Пользователь → `/bug` → описывает проблему
- Бот отправляет в Core API: `POST /api/v1/feedback/bug/`
- Разработчик видит в API + получает уведомление

**Пожертвования:**
- `POST /api/v1/feedback/donate/` — отправить IAM-coin разработчику
- Привязка к bug_report_id (опционально)

**Скрепка (будущее):**
- `POST /api/v1/skrepka/bug-analysis/` — ИИ-анализ бага
- Автоматический дебаг с отправкой репы и багтрека

### 3.5 Зависимости обновлены

**`services/bot-instance/requirements.txt`:**
```
telethon>=1.33
httpx>=0.27
redis>=5.0
loguru>=0.7
aiosqlite>=0.20
openai>=1.0
anthropic>=0.40
```

---

## Что проверено

- [x] Все импорты работают
- [x] LLMClient инициализируется с fallback chain
- [x] PersonalityLoader загружает личность "Ия" (3223 chars system prompt)
- [x] BotState сохраняет/загружает state
- [x] ConversationManager управляет историей
- [x] CoreAPIClient готов к отправке ошибок
- [x] 40 маршрутов в Core API (включая error-logs)

---

## Что НЕ сделано (в следующих фазах)

- [ ] Интеграция с Langflow (требует запущенного Langflow + flow)
- [ ] Скрепка (OpenClaw) для автоматического дебага
- [ ] NFT Collection контракт (FunC)
- [ ] Конструктор ботов (Zero Bot → создание дочерних экземпляров)
- [ ] Шифрование приватных ключей в БД

---

## Итого: что работает сейчас

1. **Zero Bot** — живой Telegram-бот с AI-ответами
2. **IA-Mother** — маркетплейс + клонирование ботов через Docker
3. **Core API** — REST API для всего (40 endpoints)
4. **TON Jetton** — IAM-coin с реальным контрактом
5. **Обратная связь** — баг-репорты + пожертвования
6. **Автоматический мониторинг** — ошибки ботов → Core API

---

## Следующий шаг

**Фаза 4: Скрепка + Маркетплейс скиллов**
- Скрепка (OpenClaw) для автоматического дебага
- Маркетплейс скиллов с оплатой через IAM-coin
- Публикация и установка скиллов
