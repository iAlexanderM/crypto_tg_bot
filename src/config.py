#!/usr/bin/env python3
"""
Конфигурация бота для отслеживания криптовалют.
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
# Ищем .env файл в корне проекта
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    print("⚠️ TELEGRAM_BOT_TOKEN не установлен!")
    print("Установите переменную окружения: TELEGRAM_BOT_TOKEN=ваш_токен")
    raise ValueError("Укажите TELEGRAM_BOT_TOKEN")

# Интервал обновления цен (в секундах)
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '60'))
# Проверяем разумность значения
if UPDATE_INTERVAL < 10 or UPDATE_INTERVAL > 3600:
    print(f"⚠️ UPDATE_INTERVAL={UPDATE_INTERVAL} слишком большой/маленький! Рекомендуется 10-3600 секунд")
    UPDATE_INTERVAL = 60

# Ограничение количества запросов (в минуту)
RATE_LIMIT = int(os.getenv('RATE_LIMIT', '60'))


# Расширенный список популярных криптовалют
BASE_COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "MATIC", "AVAX",
    "LINK", "UNI", "LTC", "ATOM", "NEAR", "ALGO", "VET", "ICP", "FIL", "TRX",
    "ETC", "XLM", "BCH", "APT", "ARB", "OP", "SUI", "SEI", "INJ", "TIA", "BTS"
]

QUOTE_COINS = [
    "USDT", "BTC", "ETH", "BNB", "USDC", "BUSD", "DAI", "TUSD", "USDP", "SOL"
]

# Настройки API
API_TIMEOUT = 5  # секунд
MAX_RETRIES = 2
RETRY_DELAY = 0.5  # секунд
