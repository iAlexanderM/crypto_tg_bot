#!/usr/bin/env python3
"""
Главный файл бота.
"""
import asyncio
import signal
import sys
import os
import logging

# Добавляем путь к src в sys.path для корректных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from config import TELEGRAM_BOT_TOKEN
from handlers import (
    cmd_start, cmd_help, cmd_add_pair, cmd_my_pairs, cmd_cached_price,
    handle_coin_selection, handle_range_setting,
    handle_price_check, handle_callback_query
)
from keyboards import get_main_keyboard
from models import user_settings, user_states
from monitoring import start_price_monitoring
from storage import load_user_data, save_user_data

# Настройка логирования с ротацией
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file = os.getenv('LOG_FILE', 'bot.log')
max_log_size = int(os.getenv('MAX_LOG_SIZE_MB', '10')) * 1024 * 1024  # 10MB по умолчанию
backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))  # 5 файлов по умолчанию

from logging.handlers import RotatingFileHandler

# Создаем ротирующий файловый обработчик
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=max_log_size, 
    backupCount=backup_count,
    encoding='utf-8'
)

# Создаем консольный обработчик
console_handler = logging.StreamHandler()

# Настраиваем формат
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Настраиваем логирование
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Функция для очистки старых логов
def cleanup_old_logs():
    """Очищает старые лог файлы при запуске."""
    try:
        import glob
        import time
        
        # Находим старые лог файлы (старше 7 дней)
        cutoff_time = time.time() - (7 * 24 * 60 * 60)
        log_files = glob.glob("*.log.*")
        
        for log_file in log_files:
            try:
                if os.path.getmtime(log_file) < cutoff_time:
                    os.remove(log_file)
                    logger.info(f"Удален старый лог файл: {log_file}")
            except Exception as e:
                logger.warning(f"Не удалось удалить {log_file}: {e}")
                
    except Exception as e:
        logger.warning(f"Ошибка при очистке логов: {e}")

# Событие для graceful shutdown (не используется в упрощенной версии)

async def start_existing_pairs_monitoring(application: Application) -> None:
    """Запускает мониторинг существующих пар при старте бота."""
    logger.info('Запуск мониторинга существующих пар...')
    
    if not user_settings:
        logger.info('Нет сохраненных пар для мониторинга')
        return
    
    for chat_id, pairs in user_settings.items():
        if not pairs:
            continue
            
        logger.info(f'Пользователь {chat_id}: {len(pairs)} пар')
        for pair in pairs:
            # Проверяем, не запущен ли уже мониторинг для этой пары
            symbol = f"{pair.base}{pair.quote}".upper()
            tracking_key = (chat_id, symbol)
            
            from models import websocket_connections
            if tracking_key not in websocket_connections:
                logger.info(f'Запуск мониторинга пары {pair.base}/{pair.quote} для чата {chat_id}')
                await start_price_monitoring(chat_id, pair.base, pair.quote, application.bot)
            else:
                logger.info(f'Мониторинг пары {pair.base}/{pair.quote} для чата {chat_id} уже запущен')

async def run_bot() -> None:
    """Запускает бота."""
    logger.info('Инициализация бота...')
        
    # Загружаем данные пользователей
    load_user_data()
    logger.info('Данные пользователей загружены')
    
    # Создаем приложение
    logger.info(f"Используем токен: {TELEGRAM_BOT_TOKEN[:10]}...")
    logger.info(f"🔑 Используем токен: {TELEGRAM_BOT_TOKEN[:10]}...")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    logger.info(f"Бот инициализирован с токеном: {TELEGRAM_BOT_TOKEN[:10]}...")
    logger.info(f"✅ Бот инициализирован с токеном: {TELEGRAM_BOT_TOKEN[:10]}...")

    # Простой обработчик для всех сообщений
    async def simple_handler(update: Update, context: CallbackContext) -> None:
        """Простой обработчик для всех сообщений."""
        if update.message:
            text = update.message.text
            chat_id = update.effective_chat.id
            
            logger.debug(f"Получено: '{text}' от {chat_id}")
            logger.info(f"📨 Получено: '{text}' от {chat_id}")
            
            if text == "/start":
                await cmd_start(update, context)
            elif text == "/help":
                await cmd_help(update, context)
            elif text == "/addpair":
                await cmd_add_pair(update, context)
            elif text == "/mypairs":
                await cmd_my_pairs(update, context)
            elif text == "/price":
                await cmd_cached_price(update, context)
            elif text in ["📊 Добавить пару", "📊 Установить пару криптовалют", "📈 Текущий курс", "👁️ Мои пары", "❓ Помощь"]:
                await handle_price_check(update, context)
            elif text.replace(".", "").replace("-", "").isdigit() or text == "-" or text == "Отмена":
                await handle_range_setting(update, context)
            else:
                await handle_coin_selection(update, context)
    
    # Регистрируем обработчики
    application.add_handler(MessageHandler(filters.ALL, simple_handler))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info('Запуск бота...')
    logger.info('Бот успешно запущен!')
    
    # Инициализируем приложение
    await application.initialize()
    await application.start()
    
    # Запускаем мониторинг существующих пар
    await start_existing_pairs_monitoring(application)
    
    logger.info('Бот работает...')
    logger.info("Запускаем polling для получения обновлений...")
    
    # Запускаем polling для получения обновлений
    logger.info("Начинаем polling...")
    
    try:
        logger.info("Запускаем polling с обработкой очереди...")
        
        # Запускаем polling вручную
        await application.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=False,  # НЕ очищаем очередь!
            timeout=10,
            read_timeout=10,
            write_timeout=10,
            connect_timeout=10
        )
        
        # Ждем бесконечно
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"Ошибка polling: {e}")
        logger.error(f"❌ Ошибка polling: {e}")
        raise
    finally:
        await application.stop()
        await application.shutdown()

# Обработчик сигналов завершения
def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown."""
    logger.info('Получен сигнал завершения, сохраняем данные...')
    save_user_data()
    logger.info('Данные сохранены, завершаем работу.')
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main() -> None:
    """Основная функция бота."""
    logger.info('Запуск программы...')
    
    # Настройка event loop для Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Запускаем бота
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info('Бот остановлен пользователем')
    except Exception as e:
        logger.error(f'Критическая ошибка: {e}')
        raise
    finally:
        # Закрываем HTTP сессию
        try:
            from utils import close_http_session
            loop.run_until_complete(close_http_session())
        except Exception as e:
            logger.error(f"Ошибка при закрытии HTTP сессии: {e}")
        loop.close()

if __name__ == "__main__":
    main()