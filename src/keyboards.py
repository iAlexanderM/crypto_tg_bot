#!/usr/bin/env python3
"""
Клавиатуры для бота.
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from config import BASE_COINS, QUOTE_COINS

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает главную клавиатуру."""
    keyboard = [
        ['📊 Добавить пару', '📈 Текущий курс'],
        ['👁️ Мои пары', '❓ Помощь']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_base_coin_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с базовыми валютами."""
    keyboard = []
    row = []
    
    for coin in sorted(BASE_COINS):
        row.append(coin)
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_quote_coin_keyboard(base_coin: str) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с котируемыми валютами."""
    keyboard = []
    row = []
    
    # Фильтруем список, исключая базовую валюту
    available_coins = [coin for coin in sorted(QUOTE_COINS) if coin != base_coin]
    
    for coin in available_coins:
        row.append(coin)
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_inline_keyboard() -> InlineKeyboardMarkup:
    """Возвращает inline клавиатуру с кнопкой отмены."""
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_pairs")]]
    return InlineKeyboardMarkup(keyboard)

def get_pairs_list_keyboard(pairs) -> InlineKeyboardMarkup:
    """Возвращает inline клавиатуру со списком пар."""
    keyboard = []
    
    for i, pair in enumerate(pairs, 1):
        # Создаем кнопку для каждой пары
        pair_text = f"{i}. {pair.base}/{pair.quote}"
        if pair.min_price is not None or pair.max_price is not None:
            pair_text += " 📊"
        
        keyboard.append([InlineKeyboardButton(
            pair_text, 
            callback_data=f"pair_{i-1}"
        )])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_pair_actions_keyboard(pair_index: int) -> InlineKeyboardMarkup:
    """Возвращает inline клавиатуру с действиями для пары."""
    keyboard = [
        [InlineKeyboardButton("📊 Настроить диапазон", callback_data=f"set_range_{pair_index}")],
        [InlineKeyboardButton("💰 Просмотреть курс", callback_data=f"view_price_{pair_index}")],
        [InlineKeyboardButton("🗑️ Удалить пару", callback_data=f"delete_pair_{pair_index}")],
        [InlineKeyboardButton("🔙 Назад к парам", callback_data="back_to_pairs")]
    ]
    return InlineKeyboardMarkup(keyboard)
