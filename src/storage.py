#!/usr/bin/env python3
"""
Модуль для сохранения и загрузки данных пользователей.
"""
import json
import os
import logging
from typing import Dict, List
from models import user_settings, CryptoPair

logger = logging.getLogger(__name__)

# Определяем путь к файлу данных
# В Docker контейнере файл находится в /app/user_data.json
# В локальной разработке - в корне проекта
if os.path.exists("/app/user_data.json"):
    STORAGE_FILE = "/app/user_data.json"
else:
    STORAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data.json")

def save_user_data():
    """Сохраняет данные пользователей в файл."""
    try:
        # Конвертируем данные в JSON-совместимый формат
        data_to_save = {}
        for chat_id, pairs in user_settings.items():
            data_to_save[str(chat_id)] = []
            for pair in pairs:
                data_to_save[str(chat_id)].append({
                    "base": pair.base,
                    "quote": pair.quote,
                    "min_price": pair.min_price,
                    "max_price": pair.max_price,
                    "created_at": pair.created_at.isoformat() if pair.created_at else None
                })
        
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Данные сохранены в {STORAGE_FILE}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")

def load_user_data():
    """Загружает данные пользователей из файла."""
    global user_settings
    
    if not os.path.exists(STORAGE_FILE):
        logger.info(f"Файл {STORAGE_FILE} не найден, создаем новый")
        return
    
    try:
        with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        user_settings.clear()
        for chat_id_str, pairs_data in data.items():
            chat_id = int(chat_id_str)
            user_settings[chat_id] = []
            
            for pair_data in pairs_data:
                min_price = pair_data.get("min_price")
                max_price = pair_data.get("max_price")
                
                # Логируем загруженные значения для отладки
                logger.debug(f"Загружаем пару {pair_data['base']}/{pair_data['quote']}:")
                logger.debug(f"   min_price: {min_price} (тип: {type(min_price)})")
                logger.debug(f"   max_price: {max_price} (тип: {type(max_price)})")
                
                # Обрабатываем created_at
                created_at = None
                if "created_at" in pair_data and pair_data["created_at"]:
                    try:
                        from datetime import datetime
                        created_at = datetime.fromisoformat(pair_data["created_at"])
                    except (ValueError, TypeError):
                        created_at = None
                
                pair = CryptoPair(
                    base=pair_data["base"],
                    quote=pair_data["quote"],
                    min_price=min_price,
                    max_price=max_price,
                    created_at=created_at
                )
                user_settings[chat_id].append(pair)
        
        logger.info(f"Данные загружены из {STORAGE_FILE}")
        logger.info(f"Загружено {len(user_settings)} пользователей")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}")

def cleanup_user_data():
    """Очищает файл данных при завершении работы."""
    try:
        if os.path.exists(STORAGE_FILE):
            os.remove(STORAGE_FILE)
            logger.info(f"Файл {STORAGE_FILE} удален")
    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {e}")
