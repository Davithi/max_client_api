"""Модель обновления"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from .message import Message


@dataclass
class Update:
    """Входящее обновление (новое сообщение и т.п.)"""
    type: str  # "message", "sticker", etc.
    message: Optional[Message] = None
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}

