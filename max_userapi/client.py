"""Главный клиент библиотеки max_userapi"""
import asyncio
import logging
from typing import Optional, Callable, Awaitable, List, Dict, Any
from .models import User, Dialog, Chat, Message, GroupInfo, Update, Contact
from .exceptions import ConnectionError
from .managers import AuthManager, MessagesManager, DialogsManager, GroupsManager, ContactsManager

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
        self.contacts = None
    
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
            
            # ВАЖНО: Вызываем prepare() перед любыми операциями
            # Без этого сервер Max Messenger не готов принимать запросы авторизации
            await self._asmax_client.prepare()
            
            # Инициализируем менеджеры
            self.auth = AuthManager(self._asmax_client)
            # Устанавливаем event loop для AuthManager, чтобы он мог вызывать async функции из других потоков
            try:
                loop = asyncio.get_running_loop()
                self.auth.set_event_loop(loop)
            except RuntimeError:
                # Если нет запущенного loop, попробуем получить текущий
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self.auth.set_event_loop(loop)
                except:
                    pass
            
            self.messages = MessagesManager(self._asmax_client, self._asmax_client.conn)
            self.dialogs = DialogsManager(self._asmax_client, self._asmax_client.conn)
            self.groups = GroupsManager(self._asmax_client, self._asmax_client.conn)
            self.contacts = ContactsManager(self._asmax_client, self._asmax_client.conn)
            
            # Регистрируем обработчик состояния авторизации (opcode 19)
            self._register_auth_state_handler()
            
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
    
    async def find_user_by_phone(self, phone: str) -> Optional[int]:
        """
        Поиск ID пользователя по номеру телефона
        
        Args:
            phone: Номер телефона в формате +7XXXXXXXXXX
        
        Returns:
            int: ID пользователя или None если не найден
        
        Note:
            Метод использует поиск по диалогам. Если пользователь не найден,
            вернётся None. Для точного поиска требуется исследование протокола.
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        # Пытаемся найти через диалоги
        try:
            dialogs = await self.get_dialogs(limit=100)
            for dialog in dialogs:
                # Проверяем, есть ли информация о пользователе в диалоге
                # Это упрощённая версия - в реальности нужен поиск по контактам
                pass
        except:
            pass
        
        # Если не нашли, возвращаем None
        # В будущем здесь можно добавить поиск через API контактов
        logger.warning(f"Поиск пользователя по номеру {phone} не реализован. Используйте ID пользователя.")
        return None
    
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
    
    def _register_auth_state_handler(self):
        """Регистрирует обработчик состояния авторизации (opcode 19)"""
        from Asmax.Packets.AuthTokenPacket import AuthTokenAnswerPacket
        from Asmax.Packets.struct.PacketHeader import PacketHeader
        from Asmax.Utils.MaxUtils import MaxUtils
        
        def auth_state_callback(payload: dict):
            """Callback для обработки состояния авторизации"""
            try:
                # Передаём состояние в AuthManager для парсинга профиля
                self.auth.process_auth_state(payload)
                # Передаём состояние в DialogsManager для парсинга чатов
                self.dialogs.process_auth_state(payload)
                # Передаём состояние в ContactsManager для парсинга контактов
                self.contacts.process_auth_state(payload)
                # Передаём состояние в GroupsManager для парсинга групп
                self.groups.process_auth_state(payload)
                logger.info("Состояние авторизации обработано, профиль, чаты, контакты и группы загружены в кеш")
            except Exception as e:
                logger.error(f"Ошибка при обработке состояния авторизации: {e}", exc_info=True)
        
        # Перерегистрируем AuthTokenAnswerPacket с callback
        # Ищем существующую регистрацию и обновляем её
        for r_packet in self._asmax_client.conn.registered_classes:
            if (hasattr(r_packet, 'clazz') and 
                r_packet.clazz == AuthTokenAnswerPacket):
                r_packet.custom_data['callback'] = auth_state_callback
                logger.debug("Обработчик состояния авторизации зарегистрирован")
                break
        else:
            # Если не нашли, регистрируем новый
            self._asmax_client.conn.register_packet(
                PacketHeader(MaxUtils.global_ver, 1, -1, 19),
                AuthTokenAnswerPacket,
                {"callback": auth_state_callback}
            )
            logger.debug("Обработчик состояния авторизации зарегистрирован (новый)")
    
    def _register_update_handlers(self):
        """Регистрирует обработчики входящих обновлений от Asmax"""
        # Обработчики уже регистрируются через messages.on_message/on_sticker
        # Этот метод оставлен для будущих расширений
        pass
    
    # ==================== Методы для работы с группами ====================
    
    async def create_group(self, title: str, member_ids: Optional[List[int]] = None) -> Chat:
        """
        Создать новый групповой чат с указанным названием и участниками
        
        Args:
            title: Название группы
            member_ids: Список ID участников (по умолчанию пустой список)
        
        Returns:
            Chat: Созданная группа
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        if member_ids is None:
            member_ids = []
        
        return await self.groups.create_group(title, member_ids)
    
    async def set_group_title(self, chat_id: int, new_title: str) -> GroupInfo:
        """
        Изменить название группового чата
        
        Args:
            chat_id: ID группы
            new_title: Новое название
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            group_info = await api.set_group_title(chat_id=123456, new_title="Новое название")
            print(f"Название изменено: {group_info.title}")
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.set_group_title(chat_id, new_title)
    
    async def set_group_description(self, chat_id: int, description: str) -> GroupInfo:
        """
        Изменить описание группового чата
        
        Args:
            chat_id: ID группы
            description: Новое описание
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            group_info = await api.set_group_description(chat_id=123456, description="Описание группы")
            print(f"Описание изменено: {group_info.description}")
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.update_group_description(chat_id, description)
    
    async def get_group_invite_link(self, chat_id: int, force_refresh: bool = False) -> str:
        """
        Получить приватную ссылку для приглашения в группу
        
        Примечание: По протоколу Max Messenger, запрос с revokePrivateLink: true всегда создает новую ссылку.
        Если force_refresh=False, сначала проверяется существующая ссылка через get_group_info().
        Если ссылки нет или force_refresh=True, создается новая ссылка.
        
        Args:
            chat_id: ID группы
            force_refresh: Если True - всегда создавать новую ссылку,
                          Если False - сначала проверять существующую ссылку
        
        Returns:
            str: Приватная ссылка для приглашения (например, "https://max.ru/join/...")
        
        Example:
            # Получить существующую ссылку (если есть)
            link = await api.get_group_invite_link(chat_id=123456)
            
            # Принудительно создать новую ссылку
            new_link = await api.get_group_invite_link(chat_id=123456, force_refresh=True)
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.get_group_invite_link(chat_id, force_refresh)
    
    async def revoke_group_invite_link(self, chat_id: int) -> str:
        """
        Обновить (отозвать и создать новую) приватную ссылку для приглашения в группу
        
        Args:
            chat_id: ID группы
        
        Returns:
            str: Новая приватная ссылка для приглашения
        
        Example:
            new_link = await api.revoke_group_invite_link(chat_id=123456)
            print(f"Новая ссылка: {new_link}")
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.revoke_group_invite_link(chat_id)
    
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
    
    async def update_group_options(
        self,
        chat_id: int,
        options: Dict[str, Any]
    ) -> GroupInfo:
        """
        Изменить опции (настройки) группы
        
        Args:
            chat_id: ID группы
            options: Словарь с опциями для изменения
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            # Отключить изменение названия/фото для участников (только владелец)
            await api.update_group_options(
                chat_id=123456,
                options={"ONLY_OWNER_CAN_CHANGE_ICON_TITLE": True}
            )
            
            # Включить изменение названия/фото для всех участников
            await api.update_group_options(
                chat_id=123456,
                options={"ONLY_OWNER_CAN_CHANGE_ICON_TITLE": False}
            )
            
            # Несколько опций одновременно
            await api.update_group_options(
                chat_id=123456,
                options={
                    "ONLY_OWNER_CAN_CHANGE_ICON_TITLE": True,
                    "ONLY_ADMIN_CAN_ADD_MEMBER": True,
                    "ALL_CAN_PIN_MESSAGE": False
                }
            )
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.update_group_options(chat_id, options)
    
    async def set_only_owner_can_change_icon_title(
        self,
        chat_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, что только владелец может изменять название, фото и описание чата
        
        Args:
            chat_id: ID группы
            enabled: True - только владелец может изменять, False - все участники могут
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            # Отключить для участников
            await api.set_only_owner_can_change_icon_title(chat_id=123456, enabled=True)
            
            # Включить для всех
            await api.set_only_owner_can_change_icon_title(chat_id=123456, enabled=False)
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.set_only_owner_can_change_icon_title(chat_id, enabled)
    
    async def set_only_admin_can_add_member(
        self,
        chat_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, что только админы могут добавлять участников
        
        Args:
            chat_id: ID группы
            enabled: True - только админы могут добавлять участников (приглашение по ссылке отключается автоматически),
                     False - все участники могут добавлять (приглашение по ссылке остается отключенным)
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            # Отключить для участников (только админы могут добавлять)
            await api.set_only_admin_can_add_member(chat_id=123456, enabled=True)
            
            # Включить для всех (все могут добавлять участников)
            await api.set_only_admin_can_add_member(chat_id=123456, enabled=False)
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.set_only_admin_can_add_member(chat_id, enabled)
    
    async def set_all_can_pin_message(
        self,
        chat_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, могут ли все участники закреплять сообщения
        
        Args:
            chat_id: ID группы
            enabled: True - все участники могут закреплять, False - только админы могут
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            # Разрешить всем закреплять сообщения
            await api.set_all_can_pin_message(chat_id=123456, enabled=True)
            
            # Только админы могут закреплять
            await api.set_all_can_pin_message(chat_id=123456, enabled=False)
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.set_all_can_pin_message(chat_id, enabled)
    
    async def set_members_can_see_private_link(
        self,
        chat_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, могут ли участники видеть приватную ссылку (приглашать по ссылке)
        
        Args:
            chat_id: ID группы
            enabled: True - участники могут видеть приватную ссылку, False - не могут
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            # Разрешить участникам приглашать по ссылке
            await api.set_members_can_see_private_link(chat_id=123456, enabled=True)
            
            # Запретить участникам приглашать по ссылке
            await api.set_members_can_see_private_link(chat_id=123456, enabled=False)
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.set_members_can_see_private_link(chat_id, enabled)
    
    async def set_only_admin_can_call(
        self,
        chat_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, могут ли только админы звонить в чате
        
        Args:
            chat_id: ID группы
            enabled: True - только админы могут звонить, False - все участники могут звонить
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Example:
            # Только админы могут звонить
            await api.set_only_admin_can_call(chat_id=123456, enabled=True)
            
            # Все участники могут звонить
            await api.set_only_admin_can_call(chat_id=123456, enabled=False)
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.groups.set_only_admin_can_call(chat_id, enabled)
    
    # ==================== Методы для работы с контактами ====================
    
    async def get_contacts(self, limit: int = 100, offset: int = 0) -> List[Contact]:
        """
        Получить список всех контактов
        
        Args:
            limit: Максимальное количество контактов
            offset: Смещение для пагинации
        
        Returns:
            List[Contact]: Список контактов
        
        Note:
            Использует кеш из состояния авторизации (opcode 19).
            Если кеш пуст, возвращает пустой список.
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.contacts.get_contacts(limit, offset)
    
    async def get_contact_by_id(self, contact_id: int) -> Optional[Contact]:
        """
        Получить контакт по ID
        
        Args:
            contact_id: ID контакта
        
        Returns:
            Contact или None если не найден
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.contacts.get_contact_by_id(contact_id)
    
    async def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """
        Найти контакт по номеру телефона
        
        Args:
            phone: Номер телефона (например, "+37455970717" или "37455970717")
        
        Returns:
            Contact или None если не найден
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.contacts.get_contact_by_phone(phone)
    
    async def check_phone(self, phone: str) -> Optional[Contact]:
        """
        Проверить, зарегистрирован ли номер телефона в Max Messenger
        
        Args:
            phone: Номер телефона в формате +XXXXXXXXXX (например, "+37444971140")
        
        Returns:
            Optional[Contact]: Контакт, если номер зарегистрирован, иначе None
        
        Example:
            contact = await api.check_phone("+37444971140")
            if contact:
                print(f"Номер зарегистрирован: {contact.name} (ID: {contact.id})")
            else:
                print("Номер не зарегистрирован")
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return await self.contacts.resolve_phone(phone)
    
    # ==================== Методы для работы с профилем ====================
    
    async def get_profile(self) -> Optional[User]:
        """
        Получить данные профиля текущего пользователя
        
        Returns:
            Optional[User]: Профиль пользователя или None если не загружен
        
        Note:
            Профиль загружается автоматически при авторизации из состояния авторизации (opcode 19).
            Если профиль не загружен, возвращает None.
        """
        if not self._connected:
            raise ConnectionError("Клиент не подключён")
        
        return self.auth.user
    
    def get_current_user(self) -> Optional[User]:
        """
        Получить текущего пользователя (синхронный метод)
        
        Returns:
            Optional[User]: Профиль пользователя или None если не загружен
        """
        return self.auth.user
    
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

