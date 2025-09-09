#!/usr/bin/env python3
"""
Модуль для мониторинга цен криптовалют.
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Set
from telegram import Bot
from models import user_settings, websocket_connections, alert_tracking, last_check_time, last_prices
from config import API_TIMEOUT, UPDATE_INTERVAL
from utils import get_crypto_price

# Группировка запросов для оптимизации
_pending_requests: Dict[str, asyncio.Future] = {}
_request_lock = asyncio.Lock()

logger = logging.getLogger(__name__)

# Настройки мониторинга
MIN_CHECK_INTERVAL = UPDATE_INTERVAL  # Интервал между проверками (секунды)

async def get_crypto_price_optimized(base: str, quote: str) -> Optional[float]:
    """
    Оптимизированное получение цены с группировкой запросов.
    Если уже есть запрос для этой пары, ждем его результат.
    """
    symbol = f"{base}{quote}".upper()
    
    async with _request_lock:
        # Если уже есть запрос для этой пары, ждем его результат
        if symbol in _pending_requests:
            logger.debug(f"Ожидаем результат для {symbol} (группировка запросов)")
            return await _pending_requests[symbol]
        
        # Создаем новый запрос
        future = asyncio.Future()
        _pending_requests[symbol] = future
        
        try:
            # Выполняем запрос
            price = await get_crypto_price(base, quote)
            future.set_result(price)
            return price
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            # Удаляем из pending запросов
            _pending_requests.pop(symbol, None)

async def start_price_monitoring(chat_id: int, base: str, quote: str, bot: Bot) -> None:
    """
    Запускает мониторинг цены для пары криптовалют.
    """
    symbol = f"{base}{quote}".upper()
    tracking_key = (chat_id, symbol)
    
    # Проверяем, не запущен ли уже мониторинг для этого пользователя и символа
    if tracking_key in websocket_connections:
        logger.info(f"Мониторинг {symbol} для пользователя {chat_id} уже запущен")
        return
    
    logger.info(f"Запуск мониторинга {symbol} для пользователя {chat_id}")
    
    # Инициализируем отслеживание алертов
    if tracking_key not in alert_tracking:
        alert_tracking[tracking_key] = {
            "alerted": False,  # Общий флаг - был ли отправлен алерт для этой пары
            "last_price": None
        }
    
    # Инициализируем время последней проверки
    last_check_time[tracking_key] = 0
    
    # Запускаем задачу мониторинга
    task = asyncio.create_task(monitor_price(chat_id, base, quote, bot))
    websocket_connections[tracking_key] = task
    
    logger.info(f"Мониторинг {symbol} запущен для пользователя {chat_id}")

async def monitor_price(chat_id: int, base: str, quote: str, bot: Bot) -> None:
    """
    Мониторит цену пары криптовалют и отправляет уведомления.
    """
    symbol = f"{base}{quote}".upper()
    tracking_key = (chat_id, symbol)
    
    logger.info(f"Начинаем мониторинг {symbol} для пользователя {chat_id}")
    
    while True:
        try:
            current_time = time.time()
            time_since_last_check = current_time - last_check_time[tracking_key]
            
            # Проверяем, прошла ли минута с последней проверки
            if time_since_last_check < MIN_CHECK_INTERVAL:
                sleep_time = MIN_CHECK_INTERVAL - time_since_last_check
                await asyncio.sleep(sleep_time)
                continue
            
            # Обновляем время последней проверки
            last_check_time[tracking_key] = current_time
            
            # Получаем текущую цену асинхронно с оптимизацией
            current_price = await get_crypto_price_optimized(base, quote)
            
            if current_price is None:
                logger.warning(f"Не удалось получить цену для {symbol}")
                await asyncio.sleep(MIN_CHECK_INTERVAL)
                continue
            
            # Сохраняем последнюю цену
            last_prices[tracking_key] = current_price
            
            # Находим пару пользователя
            user_pair = None
            for pair in user_settings.get(chat_id, []):
                if pair.base == base and pair.quote == quote:
                    user_pair = pair
                    break
            
            if not user_pair:
                logger.error(f"Пара {symbol} не найдена для пользователя {chat_id}")
                break
            
            # Проверяем алерты только если есть установленные диапазоны
            if user_pair.min_price is not None or user_pair.max_price is not None:
                # Создаем задачу для проверки алертов, чтобы не блокировать основной цикл
                asyncio.create_task(check_price_alerts(chat_id, symbol, current_price, user_pair, bot))
            
        except asyncio.CancelledError:
            logger.info(f"Мониторинг {symbol} для пользователя {chat_id} остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка в мониторинге {symbol} для пользователя {chat_id}: {e}")
            await asyncio.sleep(MIN_CHECK_INTERVAL)

async def check_price_alerts(chat_id: int, symbol: str, current_price: float, pair, bot: Bot) -> None:
    """
    Проверяет условия алертов и отправляет уведомления только при изменении цены.
    """
    tracking_key = (chat_id, symbol)
    
    # Инициализируем отслеживание предыдущей цены
    if "last_price" not in alert_tracking[tracking_key] or alert_tracking[tracking_key]["last_price"] is None:
        alert_tracking[tracking_key]["last_price"] = current_price
        return  # Первый запуск - не отправляем алерт
    
    last_price = alert_tracking[tracking_key]["last_price"]
    
    # Проверяем, изменилась ли цена значительно (больше чем на 0.01%)
    price_change_threshold = 0.0001  # 0.01%
    price_changed = abs(current_price - last_price) / last_price > price_change_threshold
    
    if not price_changed:
        return  # Цена не изменилась значительно - не проверяем алерты
    
    # Обновляем последнюю цену
    alert_tracking[tracking_key]["last_price"] = current_price
    
    # Проверяем, вышла ли цена за диапазон
    logger.debug(f"Проверка алертов для {symbol}: цена={current_price:.8f}, мин={pair.min_price}, макс={pair.max_price}")
    logger.debug(f"Флаг алерта: alerted={alert_tracking[tracking_key]['alerted']}")
    
    # Проверяем, вышла ли цена за диапазон (минимум или максимум)
    price_out_of_range = False
    alert_message = ""
    
    if pair.min_price is not None and current_price <= pair.min_price:
        price_out_of_range = True
        alert_message = f"🔔 АЛЕРТ! {symbol}\n"
        alert_message += f"💰 Текущая цена: {current_price:.8f}\n"
        alert_message += f"📉 Минимальная цена: {pair.min_price:.8f}\n"
        alert_message += f"📊 Цена упала ниже установленного минимума!"
        logger.info(f"🔔 ТРИГГЕР АЛЕРТА: {symbol} цена {current_price:.8f} <= минимума {pair.min_price:.8f}")
        
    elif pair.max_price is not None and current_price >= pair.max_price:
        price_out_of_range = True
        alert_message = f"🔔 АЛЕРТ! {symbol}\n"
        alert_message += f"💰 Текущая цена: {current_price:.8f}\n"
        alert_message += f"📈 Максимальная цена: {pair.max_price:.8f}\n"
        alert_message += f"📊 Цена поднялась выше установленного максимума!"
        logger.info(f"🔔 ТРИГГЕР АЛЕРТА: {symbol} цена {current_price:.8f} >= максимума {pair.max_price:.8f}")
    
    # Отправляем алерт только если цена вышла за диапазон И флаг не установлен
    if price_out_of_range and not alert_tracking[tracking_key]["alerted"]:
        try:
            await bot.send_message(chat_id=chat_id, text=alert_message)
            logger.info(f"✅ АЛЕРТ ОТПРАВЛЕН для {symbol}: {current_price:.8f}")
            alert_tracking[tracking_key]["alerted"] = True
        except Exception as e:
            logger.error(f"❌ ОШИБКА ОТПРАВКИ АЛЕРТА для {symbol}: {e}")
    elif price_out_of_range and alert_tracking[tracking_key]["alerted"]:
        logger.info(f"🔔 {symbol}: цена {current_price:.8f} все еще вне диапазона (уже уведомлен)")

async def stop_price_monitoring(chat_id: int, base: str, quote: str) -> None:
    """
    Останавливает мониторинг цены для пары криптовалют.
    """
    symbol = f"{base}{quote}".upper()
    tracking_key = (chat_id, symbol)
    
    if tracking_key in websocket_connections:
        task = websocket_connections[tracking_key]
        task.cancel()
        del websocket_connections[tracking_key]
        
        # Очищаем отслеживание алертов
        if tracking_key in alert_tracking:
            del alert_tracking[tracking_key]
        
        if tracking_key in last_check_time:
            del last_check_time[tracking_key]
        
        logger.info(f"Мониторинг {symbol} остановлен для пользователя {chat_id}")
    else:
        logger.warning(f"Мониторинг {symbol} не был запущен для пользователя {chat_id}")

async def get_current_price_for_pair(base: str, quote: str) -> Optional[float]:
    """
    Получает текущую цену пары криптовалют.
    """
    return await get_crypto_price(base, quote)