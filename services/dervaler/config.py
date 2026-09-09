"""
Конфигурация Дервалера. Все секреты — только из окружения.

ВАЖНО: сессия пользователя эквивалентна паролю администратора.
Она НИКОГДА не попадает в git: ни строка сессии, ни файл.
"""

import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
SESSION_DIR = DATA_DIR / "dervaler"
SESSION_FILE = SESSION_DIR / "session"

# Учётные данные Telegram (пользовательское приложение, не бот).
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

# Сессия: строка в env ПРИОРИТЕТНЕЕ файла (для локального запуска и CI).
DERVALER_SESSION = os.getenv("DERVALER_SESSION", "")

# Какой чат выгружаем. Обязателен — иначе воркер не стартует.
HELPER_CHAT_ID = int(os.getenv("HELPER_CHAT_ID", "0") or 0)
# Белый список: если задан, другие чаты игнорируются даже при явном вызове.
ALLOWED_CHAT_IDS = {
    int(c)
    for c in os.getenv("DERVALER_ALLOWED_CHAT_IDS", "").replace(" ", "").split(",")
    if c
}

DB_PATH = DATA_DIR / "dervaler" / "archive.sqlite3"

# Личность Дервалера — оттуда берём промпт сводки.
# Ищем в контейнере, иначе — в репозитории (локальный запуск).
_DEFAULT_PERSONALITY = Path("/app/personalities/dervaler")
_REPO_PERSONALITY = Path(__file__).resolve().parents[2] / "personalities" / "dervaler"
PERSONALITY_DIR = next(
    (p for p in (_DEFAULT_PERSONALITY, _REPO_PERSONALITY) if p.is_dir()),
    _DEFAULT_PERSONALITY,
)

# Лимиты инжеста.
BATCH_SIZE = int(os.getenv("DERVALER_BATCH_SIZE", "500"))
WAIT_TIME = float(os.getenv("DERVALER_WAIT_TIME", "1.0"))
# 0 = выгрузить весь архив без ограничения.
MAX_MESSAGES = int(os.getenv("DERVALER_MAX_MESSAGES", "0")) or None

# Куда писать статус администратору (личка). 0 = не писать.
ADMIN_ID = int(os.getenv("DERVALER_ADMIN_ID", "0") or 0)

# Допускать ли live-дозапись новых сообщений.
LIVE_UPDATES = os.getenv("DERVALER_LIVE", "true").lower() in ("1", "true", "yes")


def session_path() -> Path:
    """Путь к файлу сессии. Создаём каталог при первом обращении."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_FILE


def chat_allowed(chat_id: int) -> bool:
    """Проверка белого списка чатов."""
    if not ALLOWED_CHAT_IDS:
        return True
    return chat_id in ALLOWED_CHAT_IDS


def validate() -> list[str]:
    """Вернуть список проблем конфигурации (пустой = всё в порядке)."""
    problems = []
    if not TELEGRAM_API_ID:
        problems.append("TELEGRAM_API_ID не задан")
    if not TELEGRAM_API_HASH:
        problems.append("TELEGRAM_API_HASH не задан")
    if not DERVALER_SESSION and not Path(SESSION_FILE).exists():
        problems.append(
            "Нет сессии: задайте DERVALER_SESSION или смонтируйте файл "
            f"{SESSION_FILE}. Сессию создают один раз вручную (см. bootstrap_session.py)."
        )
    if not HELPER_CHAT_ID:
        problems.append("HELPER_CHAT_ID не задан — не знаю, какой чат выгружать")
    return problems
