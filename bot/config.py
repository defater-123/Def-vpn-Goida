import os

# Список репозиториев
REPOS_FILE = "keys/repos.txt"

# Временный файл для собранных ключей
PARSED_KEYS_FILE = "keys/parsed_keys.txt"

# Файл со статусом
STATUS_FILE = "data/status.json"

# GitHub Pages файл
PAGES_FILE = "docs/index.html"

# Настройки проверки
PING_COUNT = 2          # Количество ping запросов
PING_TIMEOUT = 3        # Таймаут в секундах
MAX_WORKERS = 10        # Максимум параллельных проверок

# Telegram (опционально)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
