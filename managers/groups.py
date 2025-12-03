"""Модуль работы с группами"""
import asyncio
from typing import List, Dict, Any, Optional
import logging
from ..models import GroupInfo, Chat
from ..exceptions import GroupNotFoundError, PermissionError, ConnectionError
from ..packets.groups import (
    CreateGroupPacket, CreateGroupAnswerPacket,
    UpdateGroupSettingsPacket, UpdateGroupSettingsAnswerPacket,
    AddGroupMembersPacket, AddGroupMembersAnswerPacket,
    RemoveGroupMembersPacket, RemoveGroupMembersAnswerPacket,
    GetAuthStatePacket,
    UpdateGroupOptionsPacket, UpdateGroupOptionsAnswerPacket,
)
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Utils.MaxUtils import MaxUtils

logger = logging.getLogger(__name__)


class GroupsManager:
    """Менеджер работы с группами"""
    
    def __init__(self, asmax_client, connection):
        """
        Args:
            asmax_client: Экземпляр Asmax.Max.Client.MaxClient
            connection: Экземпляр Asmax.Max.Connection.MaxConnection
        """
        self._client = asmax_client
        self._connection = connection
        
        # Словарь для хранения futures для ожидания ответов
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._request_counter = 0
        
        # Кеш групп из состояния авторизации
        self._groups_cache: Dict[int, GroupInfo] = {}
        self._auth_state: Optional[Dict[str, Any]] = None
        
        # Регистрируем обработчики ответов
        self._register_answer_handlers()
    
    def _register_answer_handlers(self):
        """Регистрирует обработчики ответов от сервера"""
        # Регистрируем обработчики для ответов на пакеты групп через register_packet
        # Используем AnswerPacket классы и callback механизм
        
        def create_group_callback(payload):
            """Callback для ответа на создание группы (cmd=1, opcode=64)"""
            # Ответ приходит с тем же seq, что и запрос
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    # В payload есть поле "chat" с полной информацией о группе
                    future.set_result(payload)
                    logger.info(f"Получен ответ на создание группы (seq={seq})")
        
        def update_settings_callback(success, chat_info):
            """Callback для ответа на обновление настроек"""
            seq = chat_info.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result({"success": success, "chat": chat_info})
        
        def add_members_callback(payload):
            """Callback для ответа на добавление участников"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
        
        def remove_members_callback(payload):
            """Callback для ответа на удаление участников"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
        
        def get_auth_state_callback(payload):
            """Callback для ответа на получение состояния авторизации (opcode 19, cmd=1)"""
            # AuthTokenAnswerPacket.process() не передаёт seq в payload
            # Нужно найти pending request по маркеру или использовать последний
            # Используем специальный маркер для запросов get_group_info
            # Ищем future с маркером "get_group_info"
            found = False
            for pending_seq, future in list(self._pending_requests.items()):
                if not future.done():
                    # Проверяем, есть ли маркер в future
                    if hasattr(future, '_get_group_info_marker'):
                        # Это наш запрос
                        future.set_result(payload)
                        self._pending_requests.pop(pending_seq, None)
                        logger.debug(f"Получен ответ на запрос состояния авторизации для get_group_info (seq={pending_seq})")
                        found = True
                        break
            
            # Если не нашли по маркеру, пробуем найти по seq если он есть в payload
            if not found:
                seq = payload.get("seq")
                if seq and seq in self._pending_requests:
                    future = self._pending_requests.pop(seq)
                    if not future.done():
                        future.set_result(payload)
                        logger.debug(f"Получен ответ на запрос состояния авторизации (seq={seq})")
        
        def update_options_callback(payload):
            """Callback для ответа на изменение опций группы (cmd=1, opcode=55)"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на изменение опций группы (seq={seq})")
        
        # Регистрируем пакеты в connection
        # Используем -1 для seq, чтобы ловить все пакеты с нужным opcode
        # Ответ на создание группы приходит как ReceiveMessage (opcode 128, cmd=0)
        # Перехватываем существующий ReceiveMessagePacket через control_func
        from Asmax.Packets.ReceiveMessage import ReceiveMessagePacket
        
        # Перехватываем ReceiveMessagePacket через control_func
        # ReceiveMessagePacket.process() вызывает control_func для CONTROL attaches
        def control_func(message, payload=None):
            """Обработчик CONTROL сообщений для обнаружения создания группы и добавления участников"""
            for attach in message.attaches:
                if attach.get("_type") == "CONTROL":
                    event = attach.get("event")
                    
                    if event == "new":
                        # Это уведомление о создании группы
                        # Ищем pending request для создания группы
                        for seq, future in list(self._pending_requests.items()):
                            if not future.done():
                                # Используем payload если доступен, иначе создаём из message
                                if payload and "chat" in payload:
                                    chat_data = payload["chat"]
                                else:
                                    chat_data = {
                                        "id": message.chatId,
                                        "chatId": message.chatId,
                                        "title": attach.get("title", ""),
                                        "type": "CHAT",
                                        "is_group": True
                                    }
                                future.set_result({"chat": chat_data})
                                self._pending_requests.pop(seq, None)
                                logger.info(f"Группа создана: {attach.get('title')} (ID: {message.chatId})")
                                break
                        break
                    
                    elif event == "add":
                        # Это уведомление о добавлении участников
                        # Ищем pending request для добавления участников
                        for seq, future in list(self._pending_requests.items()):
                            if not future.done():
                                # Используем payload если доступен
                                if payload and "chat" in payload:
                                    chat_data = payload["chat"]
                                else:
                                    chat_data = {
                                        "id": message.chatId,
                                        "chatId": message.chatId
                                    }
                                future.set_result({
                                    "success": True,
                                    "chat": chat_data,
                                    "seq": seq
                                })
                                self._pending_requests.pop(seq, None)
                                logger.info(f"Участники добавлены в группу {message.chatId}")
                                break
                        break
        
        # Добавляем control_func к существующему ReceiveMessagePacket
        for r_packet in self._connection.registered_classes:
            if hasattr(r_packet, 'clazz') and r_packet.clazz == ReceiveMessagePacket:
                r_packet.custom_data['control_func'] = control_func
                break
        
        # Регистрируем обработчик ответа на создание группы (cmd=1, opcode=64)
        # Это основной способ получения ответа от сервера
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 64),  # CreateGroupAnswer (cmd=1, opcode=64)
            CreateGroupAnswerPacket,
            {"callback": create_group_callback}
        )
        
        # Также оставляем обработчик для opcode 65 на случай, если сервер использует его
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 65),  # CreateGroupAnswer (альтернативный)
            CreateGroupAnswerPacket,
            {"callback": create_group_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 66),  # UpdateGroupSettingsAnswer
            UpdateGroupSettingsAnswerPacket,
            {"callback": update_settings_callback}
        )
        
        # Регистрируем общий обработчик ответа на добавление/удаление участников (cmd=1, opcode=77)
        # Opcode 77 используется для обоих операций (operation: "add" и "remove")
        # Ответ приходит с тем же opcode 77, различаем по seq в pending_requests
        def combined_members_callback(payload):
            """Общий callback для добавления и удаления участников"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на операцию с участниками (seq={seq})")
        
        # Используем один AnswerPacket для обоих случаев
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 77),  # CHAT_MEMBERS_UPDATE Answer (opcode 77)
            AddGroupMembersAnswerPacket,  # Используем один класс, структура ответа одинаковая
            {"callback": combined_members_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, UpdateGroupOptionsPacket.OPCODE),  # UpdateGroupOptionsAnswer (opcode 55)
            UpdateGroupOptionsAnswerPacket,
            {"callback": update_options_callback}
        )
        
        # Регистрируем обработчик для получения состояния авторизации (opcode 19, cmd=1)
        # Используем существующий AuthTokenAnswerPacket из Asmax
        # Проверяем, не зарегистрирован ли уже обработчик в client.py
        from Asmax.Packets.AuthTokenPacket import AuthTokenAnswerPacket
        
        # Ищем существующую регистрацию opcode 19
        existing_handler = None
        for r_packet in self._connection.registered_classes:
            if (hasattr(r_packet, 'clazz') and 
                r_packet.clazz == AuthTokenAnswerPacket and
                hasattr(r_packet, 'header') and
                r_packet.header.opcode == GetAuthStatePacket.OPCODE):
                existing_handler = r_packet
                break
        
        if existing_handler:
            # Обновляем существующий callback, чтобы он вызывал оба обработчика
            original_callback = existing_handler.custom_data.get('callback')
            
            def combined_callback(payload):
                """Комбинированный callback - вызывает оба обработчика"""
                # Сначала вызываем оригинальный callback (для client.py)
                if original_callback:
                    original_callback(payload)
                # Затем вызываем наш callback (для GroupsManager)
                get_auth_state_callback(payload)
            
            existing_handler.custom_data['callback'] = combined_callback
            logger.debug("Обработчик opcode 19 обновлён для поддержки get_group_info()")
        else:
            # Регистрируем новый обработчик
            self._connection.register_packet(
                PacketHeader(MaxUtils.global_ver, 1, -1, GetAuthStatePacket.OPCODE),  # GetAuthStateAnswer (opcode 19, cmd=1)
                AuthTokenAnswerPacket,
                {"callback": get_auth_state_callback}
        )
            logger.debug("Обработчик opcode 19 зарегистрирован для get_group_info()")
    
    def _extract_seq_from_response(self, payload: dict, header_seq: int = 0) -> int:
        """Извлечь sequence number из ответа"""
        # Sequence может быть в payload или в header пакета
        return payload.get("seq", header_seq)
    
    def _get_next_seq(self) -> int:
        """Получить следующий sequence number"""
        self._request_counter += 1
        return self._request_counter
    
    async def create_group(
        self,
        title: str,
        member_ids: List[int],
        description: Optional[str] = None
    ) -> Chat:
        """
        Создать новую группу
        
        Args:
            title: Название группы
            member_ids: Список ID пользователей для добавления
            description: Описание группы (опционально)
        
        Returns:
            Chat: Созданная группа
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос с seq
            packet = CreateGroupPacket(self._client.ws)
            packet.send_packet(title, member_ids, seq, description)
            
            logger.info(f"Отправлен запрос на создание группы '{title}' (seq={seq})")
            
            # Ждём ответ (с таймаутом)
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Парсим ответ - в payload есть поле "chat" с полной информацией
                chat_data = response.get("chat", response)
                if not chat_data:
                    # Если нет chat, используем весь payload
                    chat_data = response
                
                logger.info(f"Получен ответ на создание группы: chatId={chat_data.get('id') or chat_data.get('chatId')}")
                
                # Сохраняем созданную группу в кеш
                try:
                    group_info = GroupInfo.from_dict(chat_data)
                    if group_info and group_info.id:
                        self._groups_cache[group_info.id] = group_info
                        logger.debug(f"Созданная группа {group_info.id} добавлена в кеш")
                except Exception as e:
                    logger.warning(f"Не удалось добавить созданную группу в кеш: {e}")
                
                return Chat.from_dict(chat_data)
            
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут ожидания ответа при создании группы '{title}' (seq={seq})")
                raise GroupNotFoundError("Не удалось создать группу: таймаут ожидания ответа")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    def process_auth_state(self, auth_payload: Dict[str, Any]):
        """
        Обработать состояние авторизации и сохранить группы в кеш
        
        Args:
            auth_payload: Полный payload из AuthTokenAnswerPacket (opcode 19, cmd=1)
        """
        self._auth_state = auth_payload
        
        # Парсим группы из payload.chats (тип CHAT)
        chats_data = auth_payload.get('chats', [])
        
        for chat_data in chats_data:
            # Сохраняем только группы (type == 'CHAT')
            if chat_data.get('type') == 'CHAT':
                try:
                    group_info = GroupInfo.from_dict(chat_data)
                    if group_info and group_info.id:
                        self._groups_cache[group_info.id] = group_info
                except Exception as e:
                    logger.warning(f"Ошибка при парсинге группы {chat_data.get('id')}: {e}")
        
        logger.info(f"Обработано {len(self._groups_cache)} групп из состояния авторизации")
    
    async def get_group(self, group_id: int) -> GroupInfo:
        """
        Получить информацию о группе
        
        Использует кеш из состояния авторизации (opcode 19), полученного при login_by_token().
        
        Args:
            group_id: ID группы
        
        Returns:
            GroupInfo: Информация о группе
        
        Raises:
            GroupNotFoundError: Группа не найдена
        """
        # Сначала проверяем кеш из состояния авторизации
        if group_id in self._groups_cache:
            logger.debug(f"Группа {group_id} найдена в кеше")
            return self._groups_cache[group_id]
        
        # Если группа не в кеше, проверяем auth_state напрямую
        if self._auth_state:
            chats_data = self._auth_state.get('chats', [])
            for chat_data in chats_data:
                if chat_data.get('id') == group_id and chat_data.get('type') == 'CHAT':
                    try:
                        group_info = GroupInfo.from_dict(chat_data)
                        # Сохраняем в кеш
                        self._groups_cache[group_id] = group_info
                        logger.info(f"Группа {group_id} найдена в состоянии авторизации")
                        return group_info
                    except Exception as e:
                        logger.warning(f"Ошибка при парсинге группы {group_id}: {e}")
        
        # Группа не найдена
        raise GroupNotFoundError(f"Группа {group_id} не найдена в кеше и состоянии авторизации")
    
    async def set_group_title(self, group_id: int, new_title: str) -> GroupInfo:
        """
        Изменить название группового чата
        
        Args:
            group_id: ID группы
            new_title: Новое название
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Raises:
            GroupNotFoundError: Группа не найдена
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            packet = UpdateGroupOptionsPacket(self._client.ws)
            packet.send_packet(group_id, theme=new_title, seq=seq)
            
            logger.info(f"Отправлен запрос на изменение названия группы {group_id} на '{new_title}' (seq={seq})")
            
            # Ждём ответа
            try:
                payload = await asyncio.wait_for(future, timeout=10.0)
                
                # Извлекаем chat из ответа
                chat_data = payload.get("chat")
                if not chat_data:
                    raise GroupNotFoundError(f"Группа {group_id} не найдена в ответе")
                
                # Парсим GroupInfo из ответа
                group_info = GroupInfo.from_dict(chat_data)
                logger.info(f"Название группы {group_id} успешно изменено на '{new_title}'")
                
                return group_info
            
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут ожидания ответа при изменении названия группы (seq={seq})")
                raise PermissionError("Таймаут ожидания ответа")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def update_group_description(self, group_id: int, description: str) -> GroupInfo:
        """
        Изменить описание группового чата
        
        Args:
            group_id: ID группы
            description: Новое описание
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Raises:
            GroupNotFoundError: Группа не найдена
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            packet = UpdateGroupOptionsPacket(self._client.ws)
            packet.send_packet(group_id, description=description, seq=seq)
            
            logger.info(f"Отправлен запрос на изменение описания группы {group_id} на '{description}' (seq={seq})")
            
            # Ждём ответа
            try:
                payload = await asyncio.wait_for(future, timeout=10.0)
                
                # Извлекаем chat из ответа
                chat_data = payload.get("chat")
                if not chat_data:
                    raise GroupNotFoundError(f"Группа {group_id} не найдена в ответе")
                
                # Парсим GroupInfo из ответа
                group_info = GroupInfo.from_dict(chat_data)
                logger.info(f"Описание группы {group_id} успешно изменено на '{description}'")
                
                return group_info
                
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут ожидания ответа при изменении описания группы (seq={seq})")
                raise PermissionError("Таймаут ожидания ответа")
                
        finally:
            self._pending_requests.pop(seq, None)
    
    async def update_group_settings(
        self,
        group_id: int,
        settings: Dict[str, Any]
    ) -> None:
        """
        Изменить настройки группы
        
        Args:
            group_id: ID группы
            settings: Словарь настроек (title, description, avatar, etc.)
        
        Raises:
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос
            packet = UpdateGroupSettingsPacket(self._client.ws)
            packet.header.seq = seq
            packet.send_packet(group_id, settings)
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                success = response.get("success", True)
                
                if not success:
                    error_msg = response.get("error", "Неизвестная ошибка")
                    raise PermissionError(f"Не удалось обновить настройки: {error_msg}")
            
            except asyncio.TimeoutError:
                # В некоторых случаях сервер может не отправлять ответ
                # Если операция прошла успешно, просто продолжаем
                logger.warning("Таймаут ожидания ответа при обновлении настроек группы")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def get_group_members(self, group_id: int) -> List[int]:
        """
        Получить список участников группы
        
        Args:
            group_id: ID группы
        
        Returns:
            List[int]: Список ID участников
        
        Raises:
            GroupNotFoundError: Группа не найдена
        """
        # Используем get_group_info для получения информации, включая участников
        info = await self.get_group(group_id)
        return info.member_ids
    
    async def add_group_members(self, group_id: int, member_ids: List[int]) -> None:
        """
        Добавить участников в группу
        
        Args:
            group_id: ID группы
            member_ids: Список ID пользователей для добавления
        
        Raises:
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        if not member_ids:
            return
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос
            packet = AddGroupMembersPacket(self._client.ws)
            packet.send_packet(group_id, member_ids, seq)
            
            logger.info(f"Отправлен запрос на добавление участников в группу {group_id} (seq={seq})")
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Ответ содержит поле "chat" с обновлённой информацией о группе
                chat_data = response.get("chat")
                if chat_data:
                    logger.info(f"Участники успешно добавлены в группу {group_id}")
                    # Обновляем кеш группы, если она там есть
                    try:
                        group_info = GroupInfo.from_dict(chat_data)
                        if group_info and group_info.id:
                            self._groups_cache[group_info.id] = group_info
                            logger.debug(f"Кеш группы {group_id} обновлён")
                    except Exception as e:
                        logger.warning(f"Не удалось обновить кеш группы {group_id}: {e}")
                else:
                    logger.warning(f"Ответ на добавление участников не содержит данных о чате")
            
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при добавлении участников")
                raise PermissionError("Таймаут при добавлении участников")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def remove_group_members(self, group_id: int, member_ids: List[int]) -> None:
        """
        Удалить участников из группы
        
        Args:
            group_id: ID группы
            member_ids: Список ID пользователей для удаления
        
        Raises:
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        if not member_ids:
            return
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос
            packet = RemoveGroupMembersPacket(self._client.ws)
            packet.send_packet(group_id, member_ids, seq)
            
            logger.info(f"Отправлен запрос на удаление участников из группы {group_id} (seq={seq})")
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Ответ содержит поле "chat" с обновлённой информацией о группе
                chat_data = response.get("chat")
                if chat_data:
                    logger.info(f"Участники успешно удалены из группы {group_id}")
                    # Обновляем кеш группы, если она там есть
                    try:
                        group_info = GroupInfo.from_dict(chat_data)
                        if group_info and group_info.id:
                            self._groups_cache[group_info.id] = group_info
                            logger.debug(f"Кеш группы {group_id} обновлён")
                    except Exception as e:
                        logger.warning(f"Не удалось обновить кеш группы {group_id}: {e}")
                else:
                    logger.warning(f"Ответ на удаление участников не содержит данных о чате")
            
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при удалении участников")
                raise PermissionError("Таймаут при удалении участников")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def leave_group(self, group_id: int) -> None:
        """
        Покинуть группу
        
        Args:
            group_id: ID группы
        """
        # Покинуть группу = удалить себя из участников
        # Нужно получить свой ID, но для простоты можно использовать специальный метод
        # Или использовать remove_group_members с собственным ID
        raise NotImplementedError("leave_group() требует получения собственного user_id")
    
    async def get_group_info(self, chat_id: int) -> GroupInfo:
        """
        Получить информацию о группе
        
        Args:
            chat_id: ID группы
        
        Returns:
            GroupInfo: Информация о группе
        
        Raises:
            GroupNotFoundError: Группа не найдена
        """
        return await self.get_group(chat_id)
    
    async def update_group_options(
        self,
        group_id: int,
        options: Dict[str, Any]
    ) -> GroupInfo:
        """
        Изменить опции (настройки) группы
        
        Args:
            group_id: ID группы
            options: Словарь с опциями для изменения:
                {
                    "ONLY_OWNER_CAN_CHANGE_ICON_TITLE": True,  # Отключить изменение названия/фото для участников
                    "ONLY_ADMIN_CAN_ADD_MEMBER": False,  # Разрешить всем добавлять участников
                    "ALL_CAN_PIN_MESSAGE": True,  # Разрешить всем закреплять сообщения
                    ...
                }
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Raises:
            PermissionError: Недостаточно прав
            GroupNotFoundError: Группа не найдена
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            packet = UpdateGroupOptionsPacket(self._client.ws)
            packet.send_packet(group_id, options=options, seq=seq)
            
            logger.info(f"Отправлен запрос на изменение опций группы {group_id} (seq={seq})")
            
            # Ждём ответа
            try:
                payload = await asyncio.wait_for(future, timeout=10.0)
                
                # Извлекаем chat из ответа
                chat_data = payload.get("chat")
                if not chat_data:
                    raise GroupNotFoundError(f"Группа {group_id} не найдена в ответе")
                
                # Парсим GroupInfo из ответа
                group_info = GroupInfo.from_dict(chat_data)
                logger.info(f"Опции группы {group_id} успешно изменены")
                
                return group_info
                
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут ожидания ответа при изменении опций группы (seq={seq})")
                raise PermissionError("Таймаут ожидания ответа")
                
        finally:
            self._pending_requests.pop(seq, None)
    
    async def get_group_invite_link(self, group_id: int, force_refresh: bool = False) -> str:
        """
        Получить приватную ссылку для приглашения в группу
        
        Примечание: По протоколу Max Messenger, запрос с revokePrivateLink: true всегда создает новую ссылку.
        Если force_refresh=False, сначала проверяется существующая ссылка через get_group_info().
        Если ссылки нет или force_refresh=True, создается новая ссылка.
        
        Args:
            group_id: ID группы
            force_refresh: Если True - всегда создавать новую ссылку,
                          Если False - сначала проверять существующую ссылку в get_group_info()
        
        Returns:
            str: Приватная ссылка для приглашения (например, "https://max.ru/join/...")
        
        Raises:
            GroupNotFoundError: Группа не найдена
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Если не требуется принудительное обновление, сначала проверяем существующую ссылку
        if not force_refresh:
            try:
                group_info = await self.get_group(group_id)
                if group_info.invite_link:
                    logger.info(f"Найдена существующая ссылка на группу {group_id}")
                    return group_info.invite_link
            except Exception as e:
                logger.debug(f"Не удалось получить существующую ссылку через get_group_info: {e}")
                # Продолжаем создавать новую ссылку
        
        # Создаём новую ссылку через revokePrivateLink: true
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            packet = UpdateGroupOptionsPacket(self._client.ws)
            packet.send_packet(group_id, revoke_private_link=True, seq=seq)
            
            logger.info(f"Отправлен запрос на создание новой ссылки группы {group_id} (seq={seq})")
            
            # Ждём ответа
            try:
                payload = await asyncio.wait_for(future, timeout=10.0)
                
                # Извлекаем chat из ответа
                chat_data = payload.get("chat")
                if not chat_data:
                    raise GroupNotFoundError(f"Группа {group_id} не найдена в ответе")
                
                # Извлекаем ссылку
                invite_link = chat_data.get("link")
                if not invite_link:
                    raise PermissionError("Не удалось получить ссылку на группу")
                
                logger.info(f"Новая ссылка на группу {group_id} успешно создана")
                
                return invite_link
                
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут ожидания ответа при получении ссылки группы (seq={seq})")
                raise PermissionError("Таймаут ожидания ответа")
                
        finally:
            self._pending_requests.pop(seq, None)
    
    async def revoke_group_invite_link(self, group_id: int) -> str:
        """
        Обновить (отозвать и создать новую) приватную ссылку для приглашения в группу
        
        Args:
            group_id: ID группы
        
        Returns:
            str: Новая приватная ссылка для приглашения
        
        Raises:
            GroupNotFoundError: Группа не найдена
            PermissionError: Недостаточно прав
        """
        return await self.get_group_invite_link(group_id, force_refresh=True)
    
    async def set_only_owner_can_change_icon_title(
        self,
        group_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, что только владелец может изменять название, фото и описание чата
        
        Args:
            group_id: ID группы
            enabled: True - только владелец может изменять, False - все участники могут
        
        Returns:
            GroupInfo: Обновленная информация о группе
        """
        return await self.update_group_options(
            group_id,
            {"ONLY_OWNER_CAN_CHANGE_ICON_TITLE": enabled}
        )
    
    async def set_only_admin_can_add_member(
        self,
        group_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, что только админы могут добавлять участников
        
        Args:
            group_id: ID группы
            enabled: True - только админы могут добавлять участников (приглашение по ссылке отключается автоматически),
                     False - все участники могут добавлять (приглашение по ссылке остается отключенным)
        
        Returns:
            GroupInfo: Обновленная информация о группе
        
        Note:
            - При enabled=True автоматически отключается "Приглашать по ссылке" (MEMBERS_CAN_SEE_PRIVATE_LINK: false)
            - При enabled=False нужно явно установить MEMBERS_CAN_SEE_PRIVATE_LINK: false, чтобы отключить приглашение по ссылке
        """
        if enabled:
            # Отключить для участников: только админы могут добавлять
            # MEMBERS_CAN_SEE_PRIVATE_LINK автоматически станет false
            options = {
                "ONLY_ADMIN_CAN_ADD_MEMBER": True
            }
        else:
            # Включить для всех: все могут добавлять участников
            # Но приглашение по ссылке остается отключенным
            options = {
                "ONLY_ADMIN_CAN_ADD_MEMBER": False,
                "MEMBERS_CAN_SEE_PRIVATE_LINK": False
            }
        
        return await self.update_group_options(group_id, options)
    
    async def set_all_can_pin_message(
        self,
        group_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, могут ли все участники закреплять сообщения
        
        Args:
            group_id: ID группы
            enabled: True - все участники могут закреплять, False - только админы могут
        
        Returns:
            GroupInfo: Обновленная информация о группе
        """
        return await self.update_group_options(
            group_id,
            {"ALL_CAN_PIN_MESSAGE": enabled}
        )
    
    async def set_members_can_see_private_link(
        self,
        group_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, могут ли участники видеть приватную ссылку (приглашать по ссылке)
        
        Args:
            group_id: ID группы
            enabled: True - участники могут видеть приватную ссылку, False - не могут
        
        Returns:
            GroupInfo: Обновленная информация о группе
        """
        return await self.update_group_options(
            group_id,
            {"MEMBERS_CAN_SEE_PRIVATE_LINK": enabled}
        )
    
    async def set_only_admin_can_call(
        self,
        group_id: int,
        enabled: bool
    ) -> GroupInfo:
        """
        Установить, могут ли только админы звонить в чате
        
        Args:
            group_id: ID группы
            enabled: True - только админы могут звонить, False - все участники могут звонить
        
        Returns:
            GroupInfo: Обновленная информация о группе
        """
        return await self.update_group_options(
            group_id,
            {"ONLY_ADMIN_CAN_CALL": enabled}
        )
