# Weather Forecast Skill

Прогноз погоды для Zero Bot. Использует OpenWeatherMap API.

## Установка

1. Получите API ключ на https://openweathermap.org/api
2. Установите скилл на вашего бота через маркетплейс IA-Mother
3. Настройте `api_key` в панели управления

## Использование

- `/weather Moscow` — погода в Москве
- `/weather` — погода по умолчанию (Москва)
- "какая погода в Лондоне" — естественный язык

## Разработка

```bash
# Тесты
pip install -r requirements.txt
pip install pytest pytest-asyncio
pytest tests/ -v

# Локальный тест
python -c "from handler import WeatherSkill; print('OK')"
```

## Публикация

```bash
git tag v1.0.0
git push --tags
# GitLab CI автоматически опубликует в маркетплейсе
```
