#!/usr/bin/env python3
"""
Обработчики команд для бота.
"""
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models import CryptoPair, UserState, user_settings, user_states
import logging
import asyncio
from keyboards import (
    get_main_keyboard, get_base_coin_keyboard, get_quote_coin_keyboard,
    get_cancel_inline_keyboard, 
    get_pairs_list_keyboard, get_pair_actions_keyboard
)
from monitoring import start_price_monitoring, stop_price_monitoring
from utils import validate_price
from decorators import rate_limit
from storage import save_user_data
from config import RATE_LIMIT

# Ограничения для команд (вызовов/период в секундах)
COMMAND_LIMITS = {
    'base': (5, 60),    # 5 вызовов в минуту
    'quick': (30, 60),   # 30 вызовов в минуту (увеличено для основных кнопок)
    'normal': (RATE_LIMIT, 60),  # Настраиваемое количество вызовов в минуту
}

@rate_limit(calls=COMMAND_LIMITS['quick'][0], period=COMMAND_LIMITS['quick'][1])
async def cmd_help(update: Update, context: CallbackContext) -> None:
    """Показывает справку по использованию бота."""
    help_text = (
        "🤖 *Crypto Price Alert Bot*\n\n"
        "📊 *Мониторинг:* Цены обновляются каждую минуту\n"
        "🔔 *Уведомления:* При выходе за установленные диапазоны\n\n"
        "Основные функции:\n"
        "🚀 Начать работу - Начать работу с ботом\n"
        "❓ Помощь - Показать это сообщение\n"
        "📊 Добавить пару - Добавить новую пару для отслеживания\n"
        "👁️ Мои пары - Просмотреть и управлять отслеживаемыми парами\n"
        "📈 Текущие цены - Получить текущую цену для пары\n\n"
        "📈 *Как использовать бот:*\n"
        "1. Нажмите '📊 Добавить пару' для добавления новой пары\n"
        "2. Выберите базовую и котируемую валюты\n"
        "3. Установите диапазон цен для уведомлений\n"
        "4. Бот будет отправлять уведомления при достижении указанных цен\n\n"
        "⚙️ *Дополнительно:*\n"
        "- Используйте '👁️ Мои пары' для управления парами\n"
        "- Нажмите '📈 Текущие цены' для быстрой проверки текущей цены"
    )
    
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@rate_limit(calls=COMMAND_LIMITS['quick'][0], period=COMMAND_LIMITS['quick'][1])
async def cmd_start(update: Update, context: CallbackContext) -> None:
    """Начало работы с ботом."""
    import logging
    logger = logging.getLogger(__name__)
    
    chat_id = update.effective_chat.id
    logger.info(f"🚀 cmd_start вызван для пользователя {chat_id}")
    # Логирование запуска бота
    
    # Инициализация пользователя
    if chat_id not in user_settings:
        user_settings[chat_id] = []
        logger.info(f"Создан новый пользователь {chat_id}")
    if chat_id not in user_states:
        user_states[chat_id] = UserState()
        logger.info(f"Создано состояние для пользователя {chat_id}")
    
    welcome_text = (
        "👋 Привет! Я помогу отслеживать цены криптовалют.\n\n"
        "📊 *Мониторинг:* Цены обновляются каждую минуту\n"
        "🔔 *Уведомления:* При выходе за установленные диапазоны\n\n"
        "Выберите действие:"
    )
    
    keyboard = get_main_keyboard()
    logger.info(f"Отправляем приветственное сообщение пользователю {chat_id}")
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    logger.info(f"Приветственное сообщение отправлено пользователю {chat_id}")

@rate_limit(calls=COMMAND_LIMITS['base'][0], period=COMMAND_LIMITS['base'][1])
async def cmd_add_pair(update: Update, context: CallbackContext) -> None:
    """Начинает процесс добавления новой пары."""
    import logging
    logger = logging.getLogger(__name__)
    
    chat_id = update.effective_chat.id
    logger.info(f"cmd_add_pair вызван для пользователя {chat_id}")
    
    user_states[chat_id] = UserState(current_action='selecting_base')
    logger.info(f"Установлено состояние 'selecting_base' для пользователя {chat_id}")
    
    keyboard = get_base_coin_keyboard()
    logger.info(f"Отправляем клавиатуру выбора базовой валюты пользователю {chat_id}")
    await update.message.reply_text(
        "Выберите базовую валюту:",
        reply_markup=keyboard
    )
    logger.info(f"Клавиатура отправлена пользователю {chat_id}")

@rate_limit(calls=COMMAND_LIMITS['normal'][0], period=COMMAND_LIMITS['normal'][1])
async def handle_coin_selection(update: Update, context: CallbackContext) -> None:
    """Обрабатывает выбор монеты."""
    import logging
    logger = logging.getLogger(__name__)
    
    chat_id = update.effective_chat.id
    state = user_states.get(chat_id)
    selected_coin = update.message.text
    
    logger.info(f"handle_coin_selection вызван для пользователя {chat_id} с текстом: '{selected_coin}'")
    logger.debug(f"Обработка сообщения: '{selected_coin}' от пользователя {chat_id}")
    
    # Проверяем, что пользователь находится в процессе выбора монет
    if not state or not state.current_action or state.current_action not in ['selecting_base', 'selecting_quote']:
        logger.info(f"Пользователь {chat_id} не в процессе выбора монет, игнорируем сообщение")
        logger.warning(f"Пользователь {chat_id} не в процессе выбора монет (состояние: {state.current_action if state else 'None'})")
        
        # Отправляем сообщение пользователю, если он не в процессе выбора
        await update.message.reply_text(
            "❌ Неизвестная команда. Используйте кнопку '🚀 Начать работу' для начала работы.",
            reply_markup=get_main_keyboard()
        )
        return
    
    if state.is_loading:
        logger.info(f"Пользователь {chat_id} в состоянии загрузки, игнорируем сообщение")
        return
    
    # Обработка кнопок отмены и назад
    if selected_coin in ["Отмена", "🔙 Назад"]:
        user_states[chat_id] = UserState()
        await update.message.reply_text(
            "👋 Привет! Я помогу отслеживать цены криптовалют.\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
        
    if state.current_action == 'selecting_base':
        state.selected_base = selected_coin
        state.current_action = 'selecting_quote'
        
        keyboard = get_quote_coin_keyboard(selected_coin)
        await update.message.reply_text(
            f"Выбрана базовая валюта: {selected_coin}\n\nТеперь выберите котируемую валюту:",
            reply_markup=keyboard
        )
        
    elif state.current_action == 'selecting_quote':
        state.selected_quote = selected_coin
        
        # Проверяем, не существует ли уже такая пара
        if chat_id in user_settings:
            for existing_pair in user_settings[chat_id]:
                if (existing_pair.base == state.selected_base and 
                    existing_pair.quote == selected_coin):
                    await update.message.reply_text(
                        f"❌ Пара {state.selected_base}/{selected_coin} уже существует!\n\nВыберите действие:",
                        reply_markup=get_main_keyboard()
                    )
                    user_states[chat_id] = UserState()
                    return
        
        # Создаем новую пару без диапазона
        new_pair = CryptoPair(
            base=state.selected_base,
            quote=selected_coin,
            min_price=None,
            max_price=None
        )
        
        # Добавляем пару в настройки пользователя
        if chat_id not in user_settings:
            user_settings[chat_id] = []
        user_settings[chat_id].append(new_pair)
        
        # Запускаем мониторинг
        await start_price_monitoring(chat_id, new_pair.base, new_pair.quote, context.bot)
        
        # Отправляем подтверждение
        await update.message.reply_text(
            f"✅ Пара {new_pair.base}/{new_pair.quote} добавлена!\n\n"
            f"💡 Цена будет обновляться каждую минуту\n"
            f"💡 Для установки диапазона цен используйте 'Мои пары'\n\n"
            f"Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        
        # Сбрасываем состояние
        user_states[chat_id] = UserState()
        
        # Сохраняем данные асинхронно
        asyncio.create_task(asyncio.to_thread(save_user_data))


@rate_limit(calls=COMMAND_LIMITS['quick'][0], period=COMMAND_LIMITS['quick'][1])
async def cmd_my_pairs(update: Update, context: CallbackContext) -> None:
    """Показывает список отслеживаемых пар."""
    chat_id = update.effective_chat.id
    pairs = user_settings.get(chat_id, [])
    
    if not pairs:
        await update.message.reply_text(
            "У вас нет отслеживаемых пар. Используйте '📊 Добавить пару' чтобы добавить.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем текст с информацией о парах
    pairs_text = "📊 Ваши отслеживаемые пары:\n\n"
    for i, pair in enumerate(pairs, 1):
        pairs_text += f"{i}. {pair.base}/{pair.quote}"
        if pair.min_price is not None or pair.max_price is not None:
            pairs_text += " 📊"
        pairs_text += "\n"
    
    pairs_text += "\n💡 Нажмите на пару для управления:"
    
    keyboard = get_pairs_list_keyboard(pairs)
    await update.message.reply_text(
        pairs_text,
        reply_markup=keyboard
    )

@rate_limit(calls=COMMAND_LIMITS['normal'][0], period=COMMAND_LIMITS['normal'][1])
async def handle_range_setting(update: Update, context: CallbackContext) -> None:
    """Обрабатывает ввод диапазона цен."""
    logger = logging.getLogger(__name__)
    
    chat_id = update.effective_chat.id
    state = user_states.get(chat_id)
    
    if not state or state.current_action != 'setting_range':
        return
    
    price_input = update.message.text
    
    # Обработка кнопки отмены
    if price_input == "Отмена":
        user_states[chat_id] = UserState()
        await update.message.reply_text(
            "👋 Привет! Я помогу отслеживать цены криптовалют.\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
        return
        
    # Проверка корректности введенной цены
    is_valid, price, error_message = validate_price(price_input)
    
    if not is_valid and price_input != '-':
        await update.message.reply_text(
            f"❌ {error_message}. Введите положительное число или '-' для пропуска."
        )
        return
        
    # Обработка минимальной цены
    if state.range_min is None:
        state.range_min = price
        
        # Получаем последнюю сохраненную цену из мониторинга для справки
        symbol = f"{state.selected_base}{state.selected_quote}".upper()
        tracking_key = (chat_id, symbol)
        
        from models import last_prices
        if tracking_key in last_prices:
            formatted_price = f"{last_prices[tracking_key]:.8f}"
            price_text = f"Текущий курс: `{formatted_price}`"
        else:
            price_text = "Текущий курс: ⏳ Ожидание обновления..."
        
        # Показываем точное значение, которое ввел пользователь
        await update.message.reply_text(
            f"✅ Минимальная цена установлена: {price_input}\n\n"
            f"{price_text}\n\n"
            f"Введите максимальную цену для оповещения (или '-' чтобы пропустить):",
            parse_mode='Markdown'
        )
        return
        
    # Обработка максимальной цены
    state.range_max = price
    
    # Проверка корректности диапазона
    if state.range_min is not None and state.range_max is not None:
        if state.range_min >= state.range_max:
            await update.message.reply_text(
                "❌ Минимальная цена должна быть меньше максимальной. Попробуйте снова:",
                reply_markup=get_main_keyboard()
            )
            user_states[chat_id] = UserState()
            return
        
    # Обновляем пару в настройках пользователя
    pairs = user_settings.get(chat_id, [])
    for pair in pairs:
        if pair.base == state.selected_base and pair.quote == state.selected_quote:
            pair.min_price = state.range_min
            pair.max_price = state.range_max
            break
        
    # Сбрасываем флаг алерта при изменении диапазона
    symbol = f"{state.selected_base}{state.selected_quote}".upper()
    tracking_key = (chat_id, symbol)
    from models import alert_tracking
    if tracking_key in alert_tracking:
        alert_tracking[tracking_key]["alerted"] = False
        alert_tracking[tracking_key]["last_price"] = None  # Сбрасываем отслеживание цены
        logger.info(f"Сброшен флаг алерта для {symbol} при изменении диапазона")
    
    # Отправляем подтверждение
    range_text = ""
    if state.range_min is not None:
        range_text += f"\nМинимум: {state.range_min}"
    if state.range_max is not None:
        range_text += f"\nМаксимум: {state.range_max}"
        
    await update.message.reply_text(
        f"✅ Диапазон для {state.selected_base}/{state.selected_quote} установлен!{range_text}\n\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )
    
    # Сбрасываем состояние
    user_states[chat_id] = UserState()
    
    # Сохраняем данные асинхронно
    asyncio.create_task(asyncio.to_thread(save_user_data))

@rate_limit(calls=COMMAND_LIMITS['quick'][0], period=COMMAND_LIMITS['quick'][1])
async def cmd_cached_price(update: Update, context: CallbackContext) -> None:
    """Показывает последние сохраненные цены всех пар пользователя (без запросов к API)."""
    import logging
    logger = logging.getLogger(__name__)
    
    chat_id = update.effective_chat.id
    pairs = user_settings.get(chat_id, [])
    
    logger.info(f"cmd_cached_price вызван для пользователя {chat_id}")
    
    if not pairs:
        await update.message.reply_text(
            "У вас нет отслеживаемых пар. Используйте '📊 Добавить пару' чтобы добавить.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Получаем последние сохраненные цены из мониторинга
    prices_text = "💰 Последние курсы:\n\n"
    
    from models import last_prices  # Добавим хранение последних цен
    
    for i, pair in enumerate(pairs, 1):
        symbol = f"{pair.base}{pair.quote}".upper()
        tracking_key = (chat_id, symbol)
        
        if tracking_key in last_prices:
            formatted_price = f"{last_prices[tracking_key]:.8f}"
            prices_text += f"{i}. {pair.base}/{pair.quote}: `{formatted_price}`\n"
        else:
            prices_text += f"{i}. {pair.base}/{pair.quote}: ⏳ Ожидание обновления...\n"
    
    prices_text += "\n💡 Можно скопировать нажатием\n💡 Цены обновляются каждую минуту\n\nВыберите действие:"
    
    await update.message.reply_text(
        prices_text,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

@rate_limit(calls=COMMAND_LIMITS['normal'][0], period=COMMAND_LIMITS['normal'][1])
async def handle_price_check(update: Update, context: CallbackContext) -> None:
    """Обрабатывает запрос текущей цены и кнопки меню."""
    import logging
    logger = logging.getLogger(__name__)
    
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"🔍 handle_price_check вызван для пользователя {chat_id} с текстом: '{text}'")
    logger.debug(f"handle_price_check вызван для пользователя {chat_id} с текстом: '{text}'")

    # Обработка кнопок меню
    if text in ["📊 Добавить пару", "📊 Установить пару криптовалют"]:
        logger.info(f"✅ Обрабатываем кнопку 'Добавить пару' для пользователя {chat_id}")
        await cmd_add_pair(update, context)
        return
    elif text == "📈 Текущий курс":
        logger.info(f"✅ Обрабатываем кнопку 'Текущий курс' для пользователя {chat_id}")
        await cmd_cached_price(update, context)
        return
    elif text == "👁️ Мои пары":
        logger.info(f"✅ Обрабатываем кнопку 'Мои пары' для пользователя {chat_id}")
        await cmd_my_pairs(update, context)
        return
    elif text == "❓ Помощь":
        logger.info(f"✅ Обрабатываем кнопку 'Помощь' для пользователя {chat_id}")
        await cmd_help(update, context)
        return
    
    # Обработка выбора монет для проверки цены (удалено - теперь показываем все пары сразу)

@rate_limit(calls=COMMAND_LIMITS['normal'][0], period=COMMAND_LIMITS['normal'][1])
async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    """Обрабатывает callback queries от inline кнопок."""
    import logging
    logger = logging.getLogger(__name__)
    
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data
    
    logger.info(f"🔘 Получен callback: '{data}' от пользователя {chat_id}")
    logger.debug(f"Обработка callback: '{data}' от пользователя {chat_id}")
    
    try:
        await query.answer()  # Подтверждаем получение callback
        
        if data == "back_to_main":
            # Возврат в главное меню
            welcome_text = (
                "👋 Привет! Я помогу отслеживать цены криптовалют.\n\n"
                "Выберите действие:"
            )
            keyboard = get_main_keyboard()
            
            try:
                await query.edit_message_text(
                    text=welcome_text,
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.warning(f"Не удалось отредактировать сообщение: {e}")
                await query.message.reply_text(
                    text=welcome_text,
                    reply_markup=keyboard
                )
                
        elif data == "back_to_pairs":
            # Возврат к списку пар
            pairs = user_settings.get(chat_id, [])
            if not pairs:
                await query.edit_message_text(
                    "У вас нет отслеживаемых пар. Используйте '📊 Добавить пару' чтобы добавить.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            pairs_text = "📊 Ваши отслеживаемые пары:\n\n"
            for i, pair in enumerate(pairs, 1):
                pairs_text += f"{i}. {pair.base}/{pair.quote}"
                if pair.min_price is not None or pair.max_price is not None:
                    pairs_text += " 📊"
                pairs_text += "\n"
                
            pairs_text += "\n💡 Нажмите на пару для управления:"
            
            keyboard = get_pairs_list_keyboard(pairs)
            await query.edit_message_text(
                text=pairs_text,
                reply_markup=keyboard
            )
            
        elif data.startswith("pair_"):
            # Выбор пары для управления
            pair_index = int(data.split("_")[1])
            pairs = user_settings.get(chat_id, [])
            
            logger.info(f"🔍 Обработка выбора пары {pair_index} для пользователя {chat_id}")
            logger.debug(f"Обработка выбора пары {pair_index} для пользователя {chat_id}")
            
            if 0 <= pair_index < len(pairs):
                pair = pairs[pair_index]
                
                # Показываем информацию о паре и действия
                pair_info = f"📊 Пара: {pair.base}/{pair.quote}\n\n"
                if pair.min_price is not None:
                    pair_info += f"Минимум: {pair.min_price:.8f}\n"
                else:
                    pair_info += "Минимум: не установлен\n"
                if pair.max_price is not None:
                    pair_info += f"Максимум: {pair.max_price:.8f}\n"
                else:
                    pair_info += "Максимум: не установлен\n"
                
                pair_info += "\nВыберите действие:"
                
                keyboard = get_pair_actions_keyboard(pair_index)
                logger.info(f"📊 Отправляем меню действий для пары {pair.base}/{pair.quote}")
                logger.debug(f"Отправляем меню действий для пары {pair.base}/{pair.quote}")
                
                await query.edit_message_text(
                    text=pair_info,
                    reply_markup=keyboard
                )
            else:
                logger.warning(f"❌ Пара с индексом {pair_index} не найдена для пользователя {chat_id}")
                logger.error(f"Пара с индексом {pair_index} не найдена для пользователя {chat_id}")
                await query.answer("❌ Пара не найдена")
            
        elif data.startswith("set_range_"):
            # Настройка диапазона для пары
            pair_index = int(data.split("_")[2])
            pairs = user_settings.get(chat_id, [])
            
            if 0 <= pair_index < len(pairs):
                pair = pairs[pair_index]
                user_states[chat_id] = UserState(
                    current_action='setting_range',
                    selected_base=pair.base,
                    selected_quote=pair.quote
                )
                
                # Получаем последнюю сохраненную цену из мониторинга
                symbol = f"{pair.base}{pair.quote}".upper()
                tracking_key = (chat_id, symbol)
                
                from models import last_prices
                if tracking_key in last_prices:
                    formatted_price = f"{last_prices[tracking_key]:.8f}"
                    price_text = f"Текущий курс: `{formatted_price}`"
                else:
                    price_text = "Текущий курс: ⏳ Ожидание обновления..."
                
                await query.edit_message_text(
                    f"📊 Установка диапазона для {pair.base}/{pair.quote}\n\n"
                    f"{price_text}\n\n"
                    f"Введите минимальную цену для оповещения (или '-' чтобы пропустить):",
                    reply_markup=get_cancel_inline_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Пара не найдена")
                
        elif data.startswith("view_price_"):
            # Просмотр текущей цены пары
            pair_index = int(data.split("_")[2])
            pairs = user_settings.get(chat_id, [])
            
            if 0 <= pair_index < len(pairs):
                pair = pairs[pair_index]
                
                # Получаем последнюю сохраненную цену
                symbol = f"{pair.base}{pair.quote}".upper()
                tracking_key = (chat_id, symbol)
                
                from models import last_prices
                if tracking_key in last_prices:
                    formatted_price = f"{last_prices[tracking_key]:.8f}"
                    price_text = (
                        f"💰 Последняя цена {pair.base}/{pair.quote}:\n\n"
                        f"`{formatted_price}`\n\n"
                        f"💡 Можно скопировать нажатием\n"
                        f"💡 Цены обновляются каждую минуту\n\n"
                        f"Выберите действие:"
                    )
                else:
                    price_text = (
                        f"💰 Цена {pair.base}/{pair.quote}:\n\n"
                        f"⏳ Ожидание обновления...\n\n"
                        f"💡 Цены обновляются каждую минуту\n\n"
                        f"Выберите действие:"
                    )
                
                await query.edit_message_text(
                    text=price_text,
                    reply_markup=get_pair_actions_keyboard(pair_index),
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Пара не найдена")
                
        elif data.startswith("delete_pair_"):
            # Удаление пары
            pair_index = int(data.split("_")[2])
            pairs = user_settings.get(chat_id, [])
            
            if 0 <= pair_index < len(pairs):
                pair = pairs[pair_index]
                
                # Останавливаем мониторинг и удаляем пару
                await stop_price_monitoring(chat_id, pair.base, pair.quote)
                pairs.pop(pair_index)
                
                await query.edit_message_text(
                    f"✅ Пара {pair.base}/{pair.quote} удалена.\n\nВыберите действие:",
                    reply_markup=get_pairs_list_keyboard(pairs)
                )
                
                # Сохраняем данные асинхронно
                asyncio.create_task(asyncio.to_thread(save_user_data))
            else:
                await query.answer("❌ Пара не найдена")
        
        else:
            # Неизвестный callback
            await query.answer("❌ Неизвестная команда")
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        logger.error(f"Ошибка обработки callback: {e}")
        await query.answer("❌ Произошла ошибка")
