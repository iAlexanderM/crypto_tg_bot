#!/usr/bin/env python3
"""
Модели данных для бота.
"""
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CryptoPair:
    """Модель пары криптовалют."""
    base: str
    quote: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    

@dataclass
class UserState:
    """Состояние пользователя в боте."""
    current_action: Optional[str] = None
    selected_base: Optional[str] = None
    selected_quote: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    is_loading: bool = False

# Глобальные хранилища данных
user_settings: Dict[int, List[CryptoPair]] = {}  # chat_id -> список пар
user_states: Dict[int, UserState] = {}           # chat_id -> состояние пользователя

# Архитектура мониторинга
websocket_connections: Dict[Tuple[int, str], any] = {}  # (chat_id, symbol) -> task
alert_tracking: Dict[Tuple[int, str], Dict[str, bool]] = {}  # (chat_id, symbol) -> {"min_alerted": bool, "max_alerted": bool}
last_check_time: Dict[Tuple[int, str], float] = {}  # (chat_id, symbol) -> timestamp
last_prices: Dict[Tuple[int, str], float] = {}  # (chat_id, symbol) -> последняя цена