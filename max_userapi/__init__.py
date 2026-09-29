"""max_userapi - Высокоуровневая Python-библиотека для работы с Max Messenger UserAPI"""

from .client import UserAPI
from .models import User, Dialog, Chat, Message, GroupInfo, Update, Contact
# Обратная совместимость - импорты из новой структуры
from .exceptions import (
    MaxUserAPIError,
    AuthError,
    ConnectionError,
    ChatNotFoundError,
    GroupNotFoundError,
)

__version__ = "0.1.0"
__author__ = "Your Name"
__all__ = [
    # Главный класс
    "UserAPI",
    # Модели
    "User",
    "Dialog",
    "Chat",
    "Message",
    "GroupInfo",
    "Update",
    "Contact",
    # Исключения
    "MaxUserAPIError",
    "AuthError",
    "ConnectionError",
    "ChatNotFoundError",
    "GroupNotFoundError",
]

