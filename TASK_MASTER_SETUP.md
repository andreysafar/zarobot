# Настройка Claude Task Master для Zero-Bot Constructor

## 🚀 Быстрый старт

### 1. Установка Task Master (MCP рекомендуется)

#### Для Cursor AI:
Добавьте в `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "taskmaster-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE",
        "OPENAI_API_KEY": "YOUR_OPENAI_KEY_HERE",
        "PERPLEXITY_API_KEY": "YOUR_PERPLEXITY_API_KEY_HERE"
      }
    }
  }
}
```

#### Для VS Code:
Добавьте в `<project_folder>/.vscode/mcp.json`:
```json
{
  "servers": {
    "taskmaster-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_API_KEY_HERE",
        "OPENAI_API_KEY": "YOUR_OPENAI_KEY_HERE"
      },
      "type": "stdio"
    }
  }
}
```

### 2. Инициализация проекта

В AI чате вашего редактора скажите:
```
Initialize taskmaster-ai in my project
```

### 3. Размещение файлов проекта

После инициализации Task Master создаст папку `.taskmaster/`. Скопируйте файлы:

- `PRD_FOR_TASK_MASTER.txt` → `.taskmaster/docs/prd.txt`
- `TASK_DECOMPOSITION.md` → `.taskmaster/docs/task_decomposition.md`

## 📋 Основные команды для работы

### Парсинг PRD и создание задач:
```
Can you parse my PRD at .taskmaster/docs/prd.txt and generate tasks based on the decomposition in task_decomposition.md?
```

### Планирование следующего шага:
```
What's the next task I should work on for Epoch 1: MVP Infrastructure?
```

### Реализация конкретной задачи:
```
Can you help me implement Task 1.1.1: Initialize Django project structure?
```

### Переключение между эпохами:
```
I've completed Epoch 1. Can you show me tasks for Epoch 2: Personality Modules?
```

### Проверка прогресса:
```
Show me the current status of all tasks in the MVP Infrastructure epoch
```

## 🎯 Рекомендуемый workflow

### Этап 1: Планирование
1. **Парсинг PRD**: Попросите Task Master проанализировать PRD
2. **Обзор эпох**: Изучите декомпозицию по эпохам
3. **Выбор эпохи**: Начните с Эпохи 1 (MVP Infrastructure)

### Этап 2: Реализация задач
1. **Выбор задачи**: Спросите "What's the next task?"
2. **Реализация**: Попросите помочь с конкретной задачей
3. **Проверка**: Убедитесь, что соблюдены критические требования
4. **Переход**: К следующей задаче в эпохе

### Этап 3: Контроль качества
Для каждой задачи проверяйте:
- ✅ Архитектурные принципы соблюдены
- ✅ Definition of Done выполнен
- ✅ Код соответствует спецификации

## 🔧 Примеры конкретных запросов

### Начало работы с проектом:
```
I'm starting work on Zero-Bot Constructor. Can you help me set up the initial Django project structure for Task 1.1.1? Please ensure data isolation by bot_id and follow the architecture principles from the PRD.
```

### Реализация конкретного компонента:
```
Can you help me implement the MessageRouter service for Task 1.3.1? It should route messages by bot_id and determine active personality for users. Please follow the data isolation principles.
```

### Создание репозитория личности:
```
I need to create the personality-iya repository for Task 1.4.1. Can you help me set up the base personality class and OpenAI integration following the modular architecture?
```

### Настройка Docker:
```
Can you help me create the Docker Swarm configuration for Task 1.2.1? I need django-core, mongodb, redis, langflow, and grafana services with proper networking and volumes.
```

### Интеграция платежей:
```
I'm working on Task 3.1.1 - IAM payment integration. Can you help me implement the PaymentGateway service that ensures IAM payments go to the platform, not bot owners?
```

## ⚠️ Критические напоминания для агентов

При каждой реализации напоминайте Task Master:

### Архитектурные принципы:
```
Please ensure this implementation follows these critical principles:
1. Data isolation by bot_id (NOT by user_id)
2. Each bot has unique Telegram token
3. Stars payments go to bot owner (NOT platform)
4. IAM payments go to platform (NOT bot owner)
5. Personalities are modules, NOT separate bots
6. Use Docker Swarm (NOT Kubernetes)
7. Monitor via Grafana (NOT external services)
```

### Структура данных:
```
Remember the correct data structure:
✅ /data/bots/{bot_id}/users/{user_id}/
❌ /data/users/{user_id}/bots/{bot_id}/
```

### Экономическая модель:
```
Remember the economic flow:
- IAM: Bot owners → Platform (for personalities, tools, resources)
- Stars: End users → Bot owners (for bot functions, 100% revenue)
```

## 📊 Отслеживание прогресса

### Проверка статуса эпохи:
```
Show me completion status for all tasks in Epoch 1: MVP Infrastructure
```

### Планирование следующих шагов:
```
Based on current progress, what should be the priority tasks for this week?
```

### Оценка готовности к следующей эпохе:
```
Are we ready to move from Epoch 1 to Epoch 2? What tasks are still pending?
```

## 🛠️ Troubleshooting

### Если Task Master не видит файлы:
1. Убедитесь, что файлы в правильных папках `.taskmaster/`
2. Перезапустите MCP сервер
3. Попробуйте: `Refresh taskmaster project files`

### Если задачи не соответствуют архитектуре:
1. Напомните принципы из `IMPLEMENTATION_CLARIFICATIONS.md`
2. Переформулируйте запрос с явным указанием ограничений
3. Проверьте соответствие каждого шага чек-листу

### Если нужна помощь с конкретной технологией:
```
I need help implementing Ollama integration for derValera personality. Can you research best practices and provide implementation guidance following our architecture?
```

---

## 📝 Следующие шаги

1. **Инициализируйте Task Master** в проекте
2. **Скопируйте PRD** в правильную папку
3. **Начните с Эпохи 1** - MVP Infrastructure
4. **Следуйте Architecture Principles** при каждой задаче
5. **Используйте чек-листы** для контроля качества

Удачи в разработке Zero-Bot Constructor! 🚀 