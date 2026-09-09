# Фаза 5: Скрепка + GitLab CI + Example Skill. Результат.

> **Исторический отчёт.** Фиксирует результат фазы на её дату и не обновляется.
> Актуальное состояние платформы — в [STATUS_REPORT.md](../STATUS_REPORT.md).

**Дата:** 2026-06-24
**Статус:** ✅ Завершено

---

## Что сделано

### 5.1 Скрепка — AI Admin Agent (`services/skrepka/`)

**Полноценный агент для мониторинга и управления платформой:**

| Возможность | Описание |
|-------------|----------|
| Мониторинг контейнеров | Проверяет health каждые 5 минут |
| Авто-рестарт | Перезапускает упавшие/нездоровые боты |
| Анализ баг-репортов | Автоматический анализ с rule-based подходом |
| Мониторинг ошибок | Группировка по ботам, алерты при высоком уровне |
| Отчётность | Статистика в Core API |

**Архитектура Скрепки:**
```
Скрепка (Docker)
├── Docker socket → мониторинг контейнеров
├── Core API → баг-репорты, логи, анализ
└── LLM (OpenRouter) → глубокий анализ багов (future)
```

**Endpoints:**
- `GET /api/v1/skrepka/health/` — health check
- `POST /api/v1/skrepka/bug-analysis/` — отправка анализа

**Dockerfile:** `services/skrepka/Dockerfile`
**Запуск:** Автоматически с остальными сервисами (без profile)

### 5.2 GitLab CI Pipeline для скиллов

**Обновлён `ci/templates/skill.gitlab-ci.yml`:**
- Все 4 стадии: validate → test → build → publish
- Validate: JSON Schema + ruff + bandit
- Test: unit + sandbox (загрузка скилла)
- Build: tar.gz пакет
- Publish: Core API + TON регистрация (manual)

**Замена Solana → TON:**
- `publish:solana` заменён на `publish:ton`
- Используется `ci/scripts/register_on_ton.py` — REST API вызов
- В future: прямая регистрация on-chain

### 5.3 Registration Script (`ci/scripts/register_on_ton.py`)

Python-скрипт для публикации скилла через Core API:
```bash
python register_on_ton.py \
  --registry-url=http://core-api:8000 \
  --token=your-token \
  --manifest=manifest.json
```

Читает manifest.json → вызывает `POST /api/v1/marketplace/skills/publish/`

### 5.4 Example Skill (`examples/skill-weather/`)

Полноценный пример скилла "Прогноз погоды":

```
examples/skill-weather/
├── manifest.json       # Манифест скилла (валидируется схемой)
├── handler.py          # WeatherSkill implements BaseSkill
├── requirements.txt    # httpx, zero-bot-sdk
├── tests/
│   └── test_handler.py # 5 тестов (pytest)
├── .gitlab-ci.yml      # CI pipeline
└── README.md           # Документация для разработчиков
```

**Фичи примера:**
- `/weather Moscow` — команда
- "какая погода в..." — естественный язык
- Настраиваемый API key через config
- Полный набор тестов (мокаем API вызовы)

### 5.5 Seed-данные

**5 категорий:** Разработка, Языки, Анализ, Творчество, Утилиты

**5 скиллов:**
1. 💻 Генерация кода Python — 25 IAM
2. 🌍 Умный переводчик — 15 IAM
3. 📊 Анализ настроения — бесплатно
4. 🛠️ Прогноз погоды — 10 IAM
5. 🎨 Генератор мемов — 20 IAM

### 5.6 Docker Compose обновлён

Скрепка теперь запускается автоматически со всеми сервисами:
```yaml
skrepka:
  build: services/skrepka/Dockerfile
  depends_on: [redis, core-api]
  volumes: [docker.sock, skrepka_data, skrepka_repos]
```

---

## Полная архитектура платформы

```
┌────────────────────────────────────────────────────────────────────┐
│                          Docker Host                                │
│                                                                     │
│  ┌───────────┐   ┌──────────┐   ┌────────┐   ┌──────────────┐     │
│  │ IA-Mother │   │ Core API │   │ Redis  │   │  Langflow    │     │
│  │ (Telethon)│──▶│ (FastAPI)│◀─▶│        │   │ (7860)       │     │
│  │           │   │          │   │        │   │              │     │
│  │ Docker    │   │ SQLite   │   │        │   │              │     │
│  │ Manager   │   │          │   │        │   │              │     │
│  └─────┬─────┘   └────┬─────┘   └────────┘   └──────────────┘     │
│        │              │                                            │
│  ┌─────┴──────────────┴─────────────────────────────────────────┐  │
│  │              Bot Instances (zero-bot-{id})                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │  │
│  │  │  Zero Bot│  │  Clone 1 │  │  Clone 2 │  ...             │  │
│  │  │ + LLM    │  │ + LLM    │  │ + LLM    │                  │  │
│  │  │ + Skills │  │ + Skills │  │ + Skills │                  │  │
│  │  └──────────┘  └──────────┘  └──────────┘                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────┐                                                       │
│  │ Скрепка  │  ← Docker + Core API + autorestart                    │
│  │ (agent)  │                                                       │
│  └──────────┘                                                       │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   TON Blockchain                               │  │
│  │  IAM-coin Jetton (EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8) │  │
│  │  + Skill Registry via Core API                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Что проверено

- [x] Скрепка импортируется и имеет все методы
- [x] Skill manifest проходит schema validation
- [x] CI template использует TON (не Solana)
- [x] Docker Compose обновлён
- [x] Полный импорт всех модулей: 47 маршрутов, OK

---

## Что осталось (TODO)

- [ ] NFT Collection FunC контракт для паспортов
- [ ] Реальная отправка TON транзакций (нужен приватный ключ)
- [ ] WebApp для конструктора ботов
- [ ] Шифрование приватных ключей в БД
- [ ] Langflow flow builder API
- [ ] Интеграция с Telegram Payments для Stars
- [ ] Alembic миграции

---

## Следующий шаг

Платформа готова к запуску. Для production нужно:
1. Заполнить `.env` реальными ключами
2. `docker compose up -d --build`
3. Настроить GitLab Runner
4. Запустить BotFather для создания ботов
