"""Главный клиент библиотеки max_userapi"""
import asyncio
import logging
from typing import Optional, Callable, Awaitable, List
from .models import User, Dialog, Chat, Message, GroupInfo, Update
from .exceptions import ConnectionError
from .auth import AuthManager
from .messages import MessagesManager
from .dialogs import DialogsManager
from .groups import GroupsManager

# Импорт из Asmax
from Asmax.Max.Client import MaxClient

logger = logging.getLogger(__name__)


class UserAPI:
    """
    Главный класс библиотеки - простой и понятный интерфейс
    
    Пример использования:
        api = UserAPI(session_name="my_session")
        await api.connect()
        await api.login_via_sms(phone="+79991234567", code_callback=lambda: input("Code: "))
        await api.send_message(chat_id=123, text="Привет")
    """
    
    def __init__(self, session_name: str, *, timeout: float = 30.0):
        """
        Инициализация клиента
        
        Args:
            session_name: Имя сессии (для сохранения токена в файле {session_name}.max)
            timeout: Таймаут операций в секундах
        """
        self.session_name = session_name
        self.timeout = timeout
        
        # Внутренний клиент Asmax
        self._asmax_client: Optional[MaxClient] = None
        self._update_handler: Optional[Callable[[Update], Awaitable[None]]] = None
        
        # Флаг подключения
        self._connected = False
        
        # Менеджеры
        self.auth = None  # Инициализируется в connect()
        self.messages = None
        self.dialogs = None
        self.groups = None
    
    async def connect(self) -> None:
        """
        Устанавливает соединение с Max через Asmax и поднимает event-loop/слушателя
        
        Raises:
            ConnectionError: Ошибка подключения
        """
        try:
            # Создаём клиент Asmax
            self._asmax_client = MaxClient(self.session_name)
            
            # Подключаемся
            self._asmax_client.connect()
            
            # Инициализируем менеджеры
            self.auth = AuthManager(self._asmax_client)
            self.messages = MessagesManager(self._asmax_client, self._asmax_client.conn)
            self.dialogs = DialogsManager(self._asmax_client, self._asmax_client.conn)
            self.groups = GroupsManager(self._asmax_client, self._asmax_client.conn)
            
            # Регистрируем обработчики обновлений
            self._register_update_handlers()
            
            self._connected = True
            logger.info("Подключение установлено")
        
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Ошибка подключения: {e}") from e
    
    async def login_via_sms(
        self,
        phone: str,
        code_callback: Optional[Callable[[str], str]] = None
    ) -> None:
        """
        Процедура авторизации: запрос кода, ввод кода, сохранение сессии
        
        Args:
            phone: Номер телефона в формате +7XXXXXXXXXX
            code_callback: Функция для получения SMS-кода.
                          Вызывается как callback(token: str) -> str
                          Если None - используется стандартный input()
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            await self.connect()
        
        await self.auth.login_via_sms(phone, code_callback)
    
    async def login_by_token(self) -> None:
        """
        Авторизация по сохранённому токену (если есть)
        
        Raises:
            ConnectionError: Клиент не подключён или токен отсутствует
        """
        if not self._connected:
            await self.connect()
        
        if not self.auth.has_token():
            raise ConnectionError("Токен не найден. Используйте login_via_sms()")
        
        await self._asmax_client.auth_by_token()
        logger.info("Авторизация по токену успешна")
    
    async def send_message(self, chat_id: int, text: str) -> Message:
        """
        Отправка текстового сообщения
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
        
        Returns:
            Message: Отправленное сообщение
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.messages.send_message(chat_id, text)
    
    async def get_dialogs(self, limit: int = 50) -> List[Dialog]:
        """
        Получение списка диалогов/чатов
        
        Args:
            limit: Максимальное количество диалогов
        
        Returns:
            list[Dialog]: Список диалогов
        
        Note:
            Метод будет реализован после исследования протокола Max Messenger.
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.dialogs.get_dialogs(limit)
    
    async def listen_updates(
        self,
        handler: Callable[[Update], Awaitable[None]]
    ) -> None:
        """
        Подписка на все входящие события (новые сообщения и т.п.)
        
        Args:
            handler: Асинхронная функция для обработки обновлений
                    handler(update: Update) -> None
        """
        self._update_handler = handler
        
        # Регистрируем обработчик сообщений
        async def message_handler(msg: Message):
            update = Update(type="message", message=msg)
            await handler(update)
        
        async def sticker_handler(msg: Message, attach: dict):
            update = Update(type="sticker", message=msg, data={"sticker": attach})
            await handler(update)
        
        self.messages.on_message(message_handler)
        self.messages.on_sticker(sticker_handler)
    
    def _register_update_handlers(self):
        """Регистрирует обработчики входящих обновлений от Asmax"""
        # Обработчики уже регистрируются через messages.on_message/on_sticker
        # Этот метод оставлен для будущих расширений
        pass
    
    # ==================== Методы для работы с группами ====================
    
    async def create_group(self, title: str, member_ids: list[int]) -> Chat:
        """
        Создать новый групповой чат с указанным названием и участниками
        
        Args:
            title: Название группы
            member_ids: Список ID участников
        
        Returns:
            Chat: Созданная группа
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.create_group(title, member_ids)
    
    async def set_group_title(self, chat_id: int, new_title: str) -> None:
        """
        Изменить название группового чата
        
        Args:
            chat_id: ID группы
            new_title: Новое название
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        await self.groups.set_group_title(chat_id, new_title)
    
    async def add_group_members(self, chat_id: int, member_ids: list[int]) -> None:
        """
        Добавить участников в группу
        
        Args:
            chat_id: ID группы
            member_ids: Список ID пользователей для добавления
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        await self.groups.add_group_members(chat_id, member_ids)
    
    async def remove_group_members(self, chat_id: int, member_ids: list[int]) -> None:
        """
        Удалить участников из группы
        
        Args:
            chat_id: ID группы
            member_ids: Список ID пользователей для удаления
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        await self.groups.remove_group_members(chat_id, member_ids)
    
    async def get_group_info(self, chat_id: int) -> GroupInfo:
        """
        Получить информацию о группе: название, участники, настройки
        
        Args:
            chat_id: ID группы
        
        Returns:
            GroupInfo: Информация о группе
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.get_group_info(chat_id)
    
    # ==================== Утилиты ====================
    
    def is_connected(self) -> bool:
        """Проверить, подключён ли клиент"""
        return (
            self._connected and
            self._asmax_client is not None and
            hasattr(self._asmax_client, 'conn') and
            hasattr(self._asmax_client.conn, 'conn') and
            self._asmax_client.conn.conn.connected
        )
    
    async def disconnect(self) -> None:
        """Отключиться от сервера"""
        if self._asmax_client and hasattr(self._asmax_client, 'ws'):
            try:
                self._asmax_client.ws.close()
            except:
                pass
        self._connected = False
        logger.info("Отключено от сервера")

