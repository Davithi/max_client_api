"""Модуль работы с группами"""
import asyncio
from typing import List, Dict, Any, Optional
import logging
from .models import GroupInfo, Chat
from .exceptions import GroupNotFoundError, PermissionError, ConnectionError
from .groups_packets import (
    CreateGroupPacket, CreateGroupAnswerPacket,
    UpdateGroupSettingsPacket, UpdateGroupSettingsAnswerPacket,
    AddGroupMembersPacket, AddGroupMembersAnswerPacket,
    RemoveGroupMembersPacket, RemoveGroupMembersAnswerPacket,
    GetChatInfoPacket, GetChatInfoAnswerPacket,
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
        
        # Регистрируем обработчики ответов
        self._register_answer_handlers()
    
    def _register_answer_handlers(self):
        """Регистрирует обработчики ответов от сервера"""
        # Регистрируем обработчики для ответов на пакеты групп через register_packet
        # Используем AnswerPacket классы и callback механизм
        
        def create_group_callback(payload):
            """Callback для ответа на создание группы"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
        
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
        
        def get_chat_info_callback(payload):
            """Callback для ответа на получение информации о чате"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
        
        # Регистрируем пакеты в connection
        # Используем -1 для seq, чтобы ловить все пакеты с нужным opcode
        # Opcode для ответов обычно cmd=1 (ответ)
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 65),  # CreateGroupAnswer
            CreateGroupAnswerPacket,
            {"callback": create_group_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 66),  # UpdateGroupSettingsAnswer
            UpdateGroupSettingsAnswerPacket,
            {"callback": update_settings_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 67),  # AddGroupMembersAnswer
            AddGroupMembersAnswerPacket,
            {"callback": add_members_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 68),  # RemoveGroupMembersAnswer
            RemoveGroupMembersAnswerPacket,
            {"callback": remove_members_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 69),  # GetChatInfoAnswer
            GetChatInfoAnswerPacket,
            {"callback": get_chat_info_callback}
        )
    
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
            # Отправляем запрос
            packet = CreateGroupPacket(self._client.ws)
            packet.header.seq = seq
            packet.send_packet(title, member_ids, description)
            
            # Ждём ответ (с таймаутом)
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Парсим ответ
                chat_data = response.get("chat", response)
                return Chat.from_dict(chat_data)
            
            except asyncio.TimeoutError:
                # Если нет ответа, создаём группу на основе отправленных данных
                # Это fallback, если протокол не возвращает полный ответ
                logger.warning("Таймаут ожидания ответа при создании группы. Используется fallback.")
                # Возвращаем Chat с минимальными данными
                # В реальности здесь должен быть chat_id из ответа
                raise GroupNotFoundError("Не удалось создать группу: таймаут ожидания ответа")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def get_group(self, group_id: int) -> GroupInfo:
        """
        Получить информацию о группе
        
        Args:
            group_id: ID группы
        
        Returns:
            GroupInfo: Информация о группе
        
        Raises:
            GroupNotFoundError: Группа не найдена
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос
            packet = GetChatInfoPacket(self._client.ws)
            packet.header.seq = seq
            packet.send_packet(group_id)
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Парсим ответ
                chat_data = response.get("chat", response)
                return GroupInfo.from_dict(chat_data)
            
            except asyncio.TimeoutError:
                raise GroupNotFoundError(f"Группа {group_id} не найдена или таймаут запроса")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def set_group_title(self, group_id: int, new_title: str) -> None:
        """
        Изменить название группового чата
        
        Args:
            group_id: ID группы
            new_title: Новое название
        
        Raises:
            GroupNotFoundError: Группа не найдена
            PermissionError: Недостаточно прав
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Используем update_group_settings с title
        await self.update_group_settings(group_id, {"title": new_title})
    
    async def update_group_description(self, group_id: int, description: str) -> None:
        """Изменить описание группы"""
        await self.update_group_settings(group_id, {"description": description})
    
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
            packet.header.seq = seq
            packet.send_packet(group_id, member_ids)
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                success = response.get("success", True)
                
                if not success:
                    error_msg = response.get("error", "Неизвестная ошибка")
                    raise PermissionError(f"Не удалось добавить участников: {error_msg}")
            
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при добавлении участников")
        
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
            packet.header.seq = seq
            packet.send_packet(group_id, member_ids)
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                success = response.get("success", True)
                
                if not success:
                    error_msg = response.get("error", "Неизвестная ошибка")
                    raise PermissionError(f"Не удалось удалить участников: {error_msg}")
            
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при удалении участников")
        
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
