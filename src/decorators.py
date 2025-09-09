#!/usr/bin/env python3
"""
Декораторы для бота.
"""
import time
import logging
from functools import wraps
from typing import Dict, List, Tuple
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# Хранилище для отслеживания запросов пользователей
user_requests: Dict[int, List[Tuple[str, float]]] = {}

def rate_limit(calls: int, period: float):
    """Декоратор для ограничения частоты вызовов команд.
    
    Args:
        calls (int): Максимальное количество вызовов
        period (float): Период в секундах
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
            current_time = time.time()
            chat_id = update.effective_chat.id
            command = update.message.text if update.message else 'callback'
            
            # Инициализируем список запросов пользователя, если его нет
            if chat_id not in user_requests:
                user_requests[chat_id] = []
            
            # Очищаем устаревшие запросы
            user_requests[chat_id] = [
                (cmd, timestamp) 
                for cmd, timestamp in user_requests[chat_id] 
                if current_time - timestamp < period
            ]
            
            # Проверяем количество запросов
            if len(user_requests[chat_id]) >= calls:
                time_to_wait = period - (current_time - user_requests[chat_id][0][1])
                if time_to_wait > 0:
                    logger.warning(f"Rate limit для пользователя {chat_id}: {len(user_requests[chat_id])}/{calls} запросов")
                    await update.message.reply_text(
                        f"⚠️ Пожалуйста, подождите {time_to_wait:.1f} секунд перед следующей командой."
                    )
                    return
                
            # Добавляем текущий запрос
            user_requests[chat_id].append((command, current_time))
            
            # Выполняем функцию
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator