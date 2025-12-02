"""Модели данных для max_userapi"""
from .user import User
from .chat import Chat, Dialog
from .message import Message
from .group import GroupInfo
from .update import Update
from .contact import Contact

__all__ = [
    'User',
    'Chat',
    'Dialog',
    'Message',
    'GroupInfo',
    'Update',
    'Contact',
]

