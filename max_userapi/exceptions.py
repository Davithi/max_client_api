"""Исключения библиотеки max_userapi"""


class MaxUserAPIError(Exception):
    """Базовое исключение библиотеки"""
    pass


class AuthError(MaxUserAPIError):
    """Ошибка авторизации"""
    pass


class ConnectionError(MaxUserAPIError):
    """Ошибка подключения"""
    pass


class ChatNotFoundError(MaxUserAPIError):
    """Чат не найден"""
    pass


class GroupNotFoundError(MaxUserAPIError):
    """Группа не найдена"""
    pass


class PermissionError(MaxUserAPIError):
    """Ошибка прав доступа"""
    pass

