"""Менеджеры для работы с Max Messenger API"""
from .auth import AuthManager
from .messages import MessagesManager
from .dialogs import DialogsManager
from .groups import GroupsManager
from .contacts import ContactsManager

__all__ = [
    'AuthManager',
    'MessagesManager',
    'DialogsManager',
    'GroupsManager',
    'ContactsManager',
]

