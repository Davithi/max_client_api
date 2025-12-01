"""Пакеты для работы с группами в Max Messenger

ВАЖНО: Opcode, используемые в этом модуле (65-69), являются предполагаемыми
и могут потребовать корректировки после исследования реального протокола Max Messenger.
Для определения правильных opcode используйте перехват WebSocket трафика.
"""
import websocket
from typing import List, Optional, Dict, Any
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Packets.struct.AnswerPacket import AnswerPacket
from Asmax.Packets.struct.Packet import Packet
from Asmax.Utils.MaxUtils import MaxUtils


class CreateGroupPacket(Packet):
    """
    Пакет для создания новой группы
    
    Note: Opcode 65 предполагается для создания группы.
    Для подтверждения используйте перехват WebSocket трафика при создании группы через приложение.
    """
    def __init__(self, ws: websocket.WebSocket):
        # Предполагаемый opcode для создания группы
        # cmd=0 означает запрос, seq будет установлен при отправке
        super().__init__(PacketHeader(11, 0, 20, 65))
        self.ws = ws
    
    def send_packet(self, title: str, member_ids: List[int], description: Optional[str] = None):
        """
        Отправить запрос на создание группы
        
        Args:
            title: Название группы
            member_ids: Список ID участников
            description: Описание группы (опционально)
        """
        payload = {
            "title": title,
            "memberIds": member_ids,
            "type": "GROUP"
        }
        
        if description:
            payload["description"] = description
        
        self.send(payload, self.ws)


class CreateGroupAnswerPacket(AnswerPacket):
    """Ответ на создание группы"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat_info = payload.get("chat", payload)
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header в payload для сопоставления
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class UpdateGroupSettingsPacket(Packet):
    """
    Пакет для обновления настроек группы (название, описание и т.д.)
    
    Note: Opcode 66 предполагается для обновления настроек группы.
    """
    def __init__(self, ws: websocket.WebSocket):
        # Предполагаемый opcode для обновления настроек группы
        super().__init__(PacketHeader(11, 0, 21, 66))
        self.ws = ws
    
    def send_packet(self, chat_id: int, settings: Dict[str, Any]):
        """
        Обновить настройки группы
        
        Args:
            chat_id: ID группы
            settings: Словарь настроек (title, description, avatar и т.д.)
        """
        payload = {
            "chatId": chat_id,
            **settings
        }
        self.send(payload, self.ws)


class UpdateGroupSettingsAnswerPacket(AnswerPacket):
    """Ответ на обновление настроек"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.success = payload.get("success", True)
        self.chat_info = payload.get("chat", {})
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header
            chat_info = self.chat_info.copy()
            chat_info["seq"] = self.header.seq
            callback(self.success, chat_info)


class AddGroupMembersPacket(Packet):
    """
    Пакет для добавления участников в группу
    
    Note: Opcode 67 предполагается для добавления участников.
    """
    def __init__(self, ws: websocket.WebSocket):
        # Предполагаемый opcode для добавления участников
        super().__init__(PacketHeader(11, 0, 22, 67))
        self.ws = ws
    
    def send_packet(self, chat_id: int, member_ids: List[int]):
        """
        Добавить участников в группу
        
        Args:
            chat_id: ID группы
            member_ids: Список ID пользователей для добавления
        """
        payload = {
            "chatId": chat_id,
            "memberIds": member_ids
        }
        self.send(payload, self.ws)


class AddGroupMembersAnswerPacket(AnswerPacket):
    """Ответ на добавление участников"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.success = payload.get("success", True)
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class RemoveGroupMembersPacket(Packet):
    """
    Пакет для удаления участников из группы
    
    Note: Opcode 68 предполагается для удаления участников.
    """
    def __init__(self, ws: websocket.WebSocket):
        # Предполагаемый opcode для удаления участников
        super().__init__(PacketHeader(11, 0, 23, 68))
        self.ws = ws
    
    def send_packet(self, chat_id: int, member_ids: List[int]):
        """
        Удалить участников из группы
        
        Args:
            chat_id: ID группы
            member_ids: Список ID пользователей для удаления
        """
        payload = {
            "chatId": chat_id,
            "memberIds": member_ids
        }
        self.send(payload, self.ws)


class RemoveGroupMembersAnswerPacket(AnswerPacket):
    """Ответ на удаление участников"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.success = payload.get("success", True)
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class GetChatInfoPacket(Packet):
    """
    Пакет для получения информации о чате/группе
    
    Note: Opcode 69 предполагается для получения информации о чате.
    """
    def __init__(self, ws: websocket.WebSocket):
        # Предполагаемый opcode для получения информации о чате
        super().__init__(PacketHeader(11, 0, 24, 69))
        self.ws = ws
    
    def send_packet(self, chat_id: int):
        """Запросить информацию о чате"""
        payload = {
            "chatId": chat_id
        }
        self.send(payload, self.ws)


class GetChatInfoAnswerPacket(AnswerPacket):
    """Ответ с информацией о чате"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat_info = payload.get("chat", payload)
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)

