#!/usr/bin/env python3
"""
Упрощенный бот для отладки
"""
import asyncio
import logging
import sys
import os

# Добавляем путь к src в sys.path для корректных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from config import TELEGRAM_BOT_TOKEN
from models import user_settings, user_states
from storage import load_user_data

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def cmd_start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    chat_id = update.effective_chat.id
    print(f"🚀 /start от пользователя {chat_id}")
    logger.info(f"🚀 /start от пользователя {chat_id}")
    
    # Инициализация пользователя
    if chat_id not in user_settings:
        user_settings[chat_id] = []
    if chat_id not in user_states:
        user_states[chat_id] = None
    
    welcome_text = (
        "👋 Привет! Я работаю!\n\n"
        "Команды:\n"
        "/start - начать\n"
        "/help - помощь\n"
        "/test - тест"
    )
    
    await update.message.reply_text(welcome_text)

async def cmd_help(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    chat_id = update.effective_chat.id
    print(f"❓ /help от пользователя {chat_id}")
    
    await update.message.reply_text("Это помощь!")

async def cmd_test(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /test."""
    chat_id = update.effective_chat.id
    print(f"🧪 /test от пользователя {chat_id}")
    
    await update.message.reply_text("Тест работает!")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обработчик всех сообщений."""
    text = update.message.text
    chat_id = update.effective_chat.id
    
    print(f"📨 Сообщение: '{text}' от {chat_id}")
    logger.info(f"📨 Сообщение: '{text}' от {chat_id}")
    
    await update.message.reply_text(
        f"✅ Получил: '{text}'\n"
        f"🆔 Ваш ID: {chat_id}\n"
        f"⏰ Время: {update.message.date}"
    )

def main():
    """Основная функция."""
    print("🚀 Запуск упрощенного бота...")
    
    # Загружаем данные пользователей
    load_user_data()
    print("✅ Данные загружены")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("test", cmd_test))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен! Отправьте /start")
    
    # Запускаем бота
    application.run_polling(
        drop_pending_updates=False,  # НЕ очищаем очередь!
        timeout=10
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
