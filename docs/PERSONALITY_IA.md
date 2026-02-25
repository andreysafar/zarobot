# Личность «Ия» — как устроена и на чём работает

## Как реализована сейчас

### 1. Данные личности (personalities/ia/)

- **manifest.json** — метаданные, модели, поведение. В `ai_model` указаны:
  - **preferred**: `google/gemini-3-pro-preview` (как в оригинале)
  - **free_model**: `gpt-4o-mini`
  - **fallback**: `gpt-4o`
- **prompts/system.txt** и **prompts/system_free.txt** — системные промпты оригинала (из answer.py).
- **prompts/greeting.txt**, **fallback.txt** — приветствие и заглушка.
- **training/examples.jsonl** — few-shot примеры.

Эти файлы **не отправляются ни в какую модель**, если не включён LLM-режим (см. ниже).

### 2. Локальный скрипт (test_zero_local.py)

- **Без API-ключей**: ответы строятся по **ключевым словам** (if "привет" → фиксированный текст, и т.д.). Никаких токенов, никакого LLM — поэтому бот «тупит» и не понимает смысл.
- **С API-ключом** (см. ниже): системный промпт личности и диалог отправляются в выбранную модель (OpenAI/Anthropic), ответ приходит от LLM — поведение как у оригинала.

## На каких токенах работал оригинал (telbot)

- **Платные пользователи**: OpenRouter → `google/gemini-3-pro-preview`, fallback: `gemini-2.5-pro`, `gpt-4o`, `gemini-pro-1.5`.
- **Бесплатные**: PiAPI → `gpt-4o-mini`, fallback: OpenRouter `gpt-4o-mini`, OpenAI, Claude Haiku.
- **Внутренние задачи** (контекст, профили, саммари): `google/gemini-flash-1.5` (OpenRouter), temperature 0.
- **Поиск в интернете**: `perplexity/llama-3.1-sonar-large-128k-online` (OpenRouter).

То есть оригинал работал на **реальных API (OpenRouter, PiAPI, OpenAI, Perplexity)** и тратил токены; текущий тестовый скрипт по умолчанию — нет.

## Оригинал (telbot.zip)

Во время очистки репозитория были удалены:

- **telbot.zip** (архив с бета-ботом),
- распакованная копия в **/tmp/telbot_extract/**.

То есть **оригинальный код в репозитории сейчас отсутствует**. Если у тебя осталась копия telbot.zip или папки с кодом — её можно снова положить в проект и подключать по необходимости.

## Как сделать «умную» Ию (как в оригинале)

В `test_zero_local.py` включён режим с реальным LLM. Приоритет: **OpenRouter** → OpenAI → Anthropic.

1. Задай в окружении один из ключей:
   - **OPENROUTER_API_KEY** — ответы через OpenRouter (рекомендуется; модели Gemini, GPT-4o и др.).
   - **OPENAI_API_KEY** — ответы через OpenAI (gpt-4o-mini или gpt-4o).
   - **ANTHROPIC_API_KEY** — ответы через Claude.

2. Для OpenRouter можно указать модель (иначе по умолчанию `google/gemini-2.0-flash-001`):
   ```bash
   export OPENROUTER_MODEL="google/gemini-2.0-flash-001"
   # или, например: openai/gpt-4o-mini, anthropic/claude-3.5-sonnet
   ```

3. Установи зависимость (один раз):
   ```bash
   pip install openai anthropic
   ```
   (для OpenRouter достаточно `openai` — используется OpenAI-совместимый API.)

4. Запусти бота:
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   python3 test_zero_local.py
   ```

При наличии ключа скрипт:

- подгружает **personalities/ia/prompts/system.txt** (или system_free.txt),
- отправляет в выбранную модель системный промпт + последние сообщения,
- отвечает текстом от LLM, а не по ключевым словам.

Так личность Ия начинает работать на тех же идеях (промпты из personalities/ia/), но на токенах выбранного провайдера (OpenAI или Anthropic), без восстановления всего кода оригинала.
