# Zero-Bot Database Setup

Этот документ описывает настройку MongoDB и Redis для Zero-Bot проекта.

## Быстрый старт с Docker Compose

### 1. Запуск баз данных

```bash
# Запуск MongoDB и Redis в фоне
docker-compose -f docker-compose.dev.yml up -d

# Проверка статуса
docker-compose -f docker-compose.dev.yml ps
```

### 2. Настройка переменных окружения

```bash
# Скопируйте пример конфигурации
cp zero_bot/config/environment.example .env

# Отредактируйте .env файл с вашими настройками
nano .env
```

### 3. Тестирование подключений

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите тесты подключения
cd zero_bot
python test_connections.py
```

## Доступ к базам данных

### MongoDB
- **URL**: `mongodb://localhost:27017`
- **Database**: `zero_bot`
- **User**: `zero_bot_app`
- **Password**: `zero_bot_password_123`
- **Admin User**: `admin` / `password123`

### MongoDB Express (Web UI)
- **URL**: http://localhost:8081
- **Login**: `admin` / `admin123`

### Redis
- **URL**: `redis://localhost:6379`
- **Password**: `redis123`
- **Database**: `0`

### Redis Commander (Web UI)
- **URL**: http://localhost:8082

## Структура базы данных

### Коллекции MongoDB

1. **bots** - Основная информация о ботах
   - Индексы: `bot_id`, `owner_wallet_address`, `telegram_token`
   - Валидация: обязательные поля, ограничения размера

2. **user_sessions** - Сессии пользователей с изоляцией по bot_id
   - Индексы: `(bot_id, user_id)`, `session_id`
   - Валидация: связь с существующим ботом

3. **message_logs** - Логи сообщений
   - Индексы: `(bot_id, user_id, created_at)`, `personality_used`
   - Валидация: типы сообщений и статусы

4. **payment_transactions** - Транзакции платежей
   - Индексы: `transaction_id`, `(bot_id, status)`
   - Валидация: типы валют и транзакций

### Принципы изоляции данных

- **Критично**: Все данные изолированы по `bot_id`
- **Путь данных**: `/data/bots/{bot_id}/users/{user_id}/`
- **Индексы**: Все составные индексы начинаются с `bot_id`

## Команды управления

### Остановка и очистка

```bash
# Остановка контейнеров
docker-compose -f docker-compose.dev.yml down

# Остановка с удалением данных
docker-compose -f docker-compose.dev.yml down -v

# Полная очистка (включая образы)
docker-compose -f docker-compose.dev.yml down -v --rmi all
```

### Резервное копирование

```bash
# Создание бэкапа MongoDB
docker exec zero_bot_mongodb mongodump --db zero_bot --out /backup

# Копирование бэкапа на хост
docker cp zero_bot_mongodb:/backup ./mongodb_backup
```

### Восстановление

```bash
# Восстановление из бэкапа
docker exec -i zero_bot_mongodb mongorestore --db zero_bot /backup/zero_bot
```

## Мониторинг

### Логи контейнеров

```bash
# Логи MongoDB
docker logs zero_bot_mongodb

# Логи Redis
docker logs zero_bot_redis

# Логи всех сервисов
docker-compose -f docker-compose.dev.yml logs -f
```

### Статистика использования

```bash
# Статистика MongoDB
docker exec zero_bot_mongodb mongo zero_bot --eval "db.stats()"

# Информация о Redis
docker exec zero_bot_redis redis-cli info
```

## Производственная настройка

### Безопасность

1. **Измените пароли** в production
2. **Настройте SSL/TLS** для внешних подключений
3. **Ограничьте доступ** к портам базы данных
4. **Включите аутентификацию** для всех сервисов

### Производительность

1. **Настройте репликацию** MongoDB
2. **Включите шардинг** для больших объемов данных
3. **Настройте Redis Cluster** для высокой доступности
4. **Мониторинг** через Grafana

### Переменные окружения для production

```bash
# Обязательно измените в production
MONGODB_PASSWORD=secure_production_password
REDIS_PASSWORD=secure_redis_password
SECRET_KEY=secure_django_secret_key
DEBUG=False
```

## Устранение неполадок

### Проблемы подключения

1. **Проверьте статус контейнеров**:
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

2. **Проверьте логи**:
   ```bash
   docker-compose -f docker-compose.dev.yml logs
   ```

3. **Проверьте сетевое подключение**:
   ```bash
   docker network ls
   docker network inspect zero_bot_zero_bot_network
   ```

### Проблемы с данными

1. **Проверьте права доступа**:
   ```bash
   docker exec zero_bot_mongodb mongo zero_bot --eval "db.runCommand({connectionStatus: 1})"
   ```

2. **Проверьте индексы**:
   ```bash
   docker exec zero_bot_mongodb mongo zero_bot --eval "db.bots.getIndexes()"
   ```

3. **Проверьте валидацию**:
   ```bash
   docker exec zero_bot_mongodb mongo zero_bot --eval "db.runCommand({listCollections: 1})"
   ```

## Дополнительные ресурсы

- [MongoDB Documentation](https://docs.mongodb.com/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [MongoEngine Documentation](http://mongoengine.org/)

## Поддержка

При возникновении проблем:

1. Проверьте логи контейнеров
2. Запустите тест подключений
3. Проверьте переменные окружения
4. Убедитесь, что порты не заняты другими процессами 