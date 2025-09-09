#!/usr/bin/env python3
"""
Утилиты для работы с API и валидации.
"""
import asyncio
import aiohttp
import time
import logging
from typing import Optional, Tuple
from config import API_TIMEOUT, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)

# Глобальный пул соединений для оптимизации HTTP запросов
_http_session = None

async def get_http_session() -> aiohttp.ClientSession:
    """Получает или создает глобальную HTTP сессию с пулом соединений."""
    global _http_session
    if _http_session is None or _http_session.closed:
        connector = aiohttp.TCPConnector(
            limit=100,  # Общий лимит соединений
            limit_per_host=30,  # Лимит соединений на хост
            ttl_dns_cache=300,  # Кэш DNS на 5 минут
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        _http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'CryptoBot/1.0'}
        )
    return _http_session

async def close_http_session():
    """Закрывает глобальную HTTP сессию."""
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
        _http_session = None

async def get_crypto_price(base: str, quote: str) -> Optional[float]:
    """
    Получает текущую цену пары криптовалют.
    Сначала пробует Binance, если не найдено - использует Binance USD цены.
    """
    symbol = f"{base}{quote}".upper()
    
    # Проверяем, является ли это символом, который нужно получать через USD цены
    # Убираем циклический импорт - проверяем напрямую
    usd_symbols = ["BTCSOL", "SOLBTC", "ETHBTC", "BNBBTC"]  # Символы, недоступные на Binance
    if symbol in usd_symbols:
        logger.debug(f"Получение цены {symbol} через Binance USD (недоступно на Binance)")
        return await get_crypto_price_binance_usd(base, quote)
    
    # Специальная обработка для BTC/SOL - получаем через обратный перевод SOL/BTC
    if symbol == "BTCSOL":
        logger.debug(f"Получение цены {symbol} через обратный перевод SOL/BTC...")
        return await get_btc_sol_reverse()
    
    # Специальная обработка для SOL/BTC - получаем напрямую с Binance
    if symbol == "SOLBTC":
        logger.debug(f"Получение цены {symbol} напрямую с Binance...")
        return await get_sol_btc_direct()
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={symbol}"
            
            session = await get_http_session()
            async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "bidPrice" in data and "askPrice" in data:
                            bid = float(data["bidPrice"])
                            ask = float(data["askPrice"])
                            mid_price = (bid + ask) / 2
                            return mid_price
                        else:
                            return None
                    elif response.status == 400:
                        # Символ не найден на Binance, пробуем через USD цены
                        logger.debug(f"Пара {symbol} не найдена на Binance, пробуем через USD цены...")
                        return await get_crypto_price_binance_usd(base, quote)
                    else:
                        return None
                    
        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    # Если Binance не сработал, пробуем через USD цены
    logger.debug(f"Binance не сработал для {symbol}, пробуем через USD цены...")
    return await get_crypto_price_binance_usd(base, quote)


async def get_crypto_price_binance_usd(base: str, quote: str) -> Optional[float]:
    """
    Получает цену пары криптовалют через Binance USD цены.
    Максимально точный метод - как у CoinMarketCap.
    """
    for attempt in range(MAX_RETRIES):
        try:
            session = await get_http_session()
            # Получаем цены обеих валют в USDT через Binance
            base_url = f"https://api.binance.com/api/v3/ticker/price?symbol={base.upper()}USDT"
            quote_url = f"https://api.binance.com/api/v3/ticker/price?symbol={quote.upper()}USDT"
            
            # Делаем параллельные запросы
            async with session.get(base_url) as base_response, \
                     session.get(quote_url) as quote_response:
                
                if base_response.status == 200 and quote_response.status == 200:
                    base_data = await base_response.json()
                    quote_data = await quote_response.json()
                    
                    base_price_usdt = float(base_data["price"])
                    quote_price_usdt = float(quote_data["price"])
                    
                    if quote_price_usdt > 0:
                        # Вычисляем цену base/quote
                        price = base_price_usdt / quote_price_usdt
                        logger.debug(f"Получена цена {base}/{quote} через Binance USD: {price:.8f}")
                        return price
                    else:
                        logger.warning(f"Нулевая цена quote для {base}/{quote}")
                        return None
                else:
                    logger.warning(f"Ошибка Binance API: base={base_response.status}, quote={quote_response.status}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут Binance для {base}/{quote}, попытка {attempt + 1}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"Ошибка при получении цены {base}/{quote} через Binance: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    logger.error(f"Не удалось получить цену {base}/{quote} через Binance после {MAX_RETRIES} попыток")
    return None



def validate_price(price_str: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Проверяет корректность введенной цены.
    Возвращает кортеж (валидность, цена, сообщение об ошибке).
    """
    if price_str == "-":
        return True, None, None
    
    try:
        # Убираем пробелы и заменяем запятую на точку
        price_str = price_str.strip().replace(",", ".")
        
        # Используем Decimal для высокой точности, затем конвертируем в float
        from decimal import Decimal, InvalidOperation
        price_decimal = Decimal(price_str)
        price = float(price_decimal)
        
        if price <= 0:
            return False, None, "Цена должна быть положительным числом"
        
        return True, price, None
    except (ValueError, InvalidOperation):
        return False, None, "Некорректный формат числа"

async def get_sol_btc_direct() -> Optional[float]:
    """
    Получает цену SOL/BTC напрямую с Binance.
    """
    for attempt in range(MAX_RETRIES):
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=SOLBTC"
            session = await get_http_session()
            async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data["price"])
                        logger.debug(f"Получена цена SOL/BTC с Binance: {price:.8f}")
                        return price
                    elif response.status == 400:
                        logger.warning("Пара SOL/BTC не найдена на Binance")
                        return None
                    else:
                        logger.warning(f"Binance API ошибка: {response.status}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут Binance для SOL/BTC, попытка {attempt + 1}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"Ошибка Binance API для SOL/BTC: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    logger.error(f"Не удалось получить SOL/BTC с Binance после {MAX_RETRIES} попыток")
    return None

async def get_btc_sol_reverse() -> Optional[float]:
    """
    Получает цену BTC/SOL через обратный перевод от SOL/BTC.
    """
    # Получаем цену SOL/BTC напрямую
    sol_btc_price = await get_sol_btc_direct()
    
    if sol_btc_price is not None and sol_btc_price > 0:
        # Вычисляем обратную цену BTC/SOL
        btc_sol_price = 1.0 / sol_btc_price
        logger.debug(f"Вычислена цена BTC/SOL: {btc_sol_price:.8f} (из SOL/BTC: {sol_btc_price:.8f})")
        return btc_sol_price
    else:
        logger.warning("Не удалось получить SOL/BTC для вычисления BTC/SOL")
        return None



