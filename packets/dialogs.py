"""Пакеты для работы с диалогами и историей сообщений в Max Messenger"""
import websocket
from typing import Optional
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Packets.struct.AnswerPacket import AnswerPacket
from Asmax.Packets.struct.Packet import Packet
from Asmax.Utils.MaxUtils import MaxUtils


class GetChatHistoryPacket(Packet):
    """
    Пакет для получения истории сообщений чата
    
    Использует opcode 49 (CHAT_HISTORY)
    """
    OPCODE = 49
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, 49))
        self.ws = ws
    
    def send_packet(
        self,
        chat_id: int,
        backward: int = 30,
        forward: int = 0,
        from_timestamp: Optional[int] = None,
        seq: int = 0
    ):
        """
        Получить историю сообщений чата
        
        Args:
            chat_id: ID чата
            backward: Количество сообщений назад (по умолчанию 30)
            forward: Количество сообщений вперёд (по умолчанию 0)
            from_timestamp: Timestamp сообщения для пагинации (опционально)
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id,
            "backward": backward,
            "forward": forward,
            "getMessages": True
        }
        
        # Если указан from_timestamp, добавляем его
        if from_timestamp is not None:
            payload["from"] = from_timestamp
        
        self.header.seq = seq
        self.send(payload, self.ws)


class GetChatHistoryAnswerPacket(AnswerPacket):
    """Ответ на получение истории чата (opcode 49, cmd=1)"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.messages = payload.get("messages", [])
    
    def process(self, custom_data: dict):
        """Обработка ответа на получение истории чата"""
        seq = self.header.seq
        callback = custom_data.get("callback")
        
        if callback:
            payload_with_seq = {
                "seq": seq,
                "messages": self.messages
            }
            callback(payload_with_seq)


class GetChatsListPacket(Packet):
    """
    Пакет для получения списка чатов с пагинацией
    
    Использует opcode 53 (CHATS_LIST)
    """
    OPCODE = 53
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, 53))
        self.ws = ws
    
    def send_packet(
        self,
        marker: Optional[str] = None,
        limit: int = 100,
        seq: int = 0
    ):
        """
        Получить список чатов с пагинацией
        
        Args:
            marker: Маркер для пагинации (опционально, для получения следующей страницы)
            limit: Количество чатов на странице (по умолчанию 100)
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {}
        
        # Добавляем limit только если он указан и больше 0
        if limit > 0:
            payload["limit"] = limit
        
        # Если указан marker, добавляем его для пагинации
        if marker is not None:
            payload["marker"] = marker
        
        self.header.seq = seq
        self.send(payload, self.ws)


class GetChatsListAnswerPacket(AnswerPacket):
    """Ответ на получение списка чатов (opcode 53, cmd=1)"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chats = payload.get("chats", [])
        self.marker = payload.get("marker")  # Маркер для следующей страницы
    
    def process(self, custom_data: dict):
        """Обработка ответа на получение списка чатов"""
        seq = self.header.seq
        callback = custom_data.get("callback")
        
        if callback:
            payload_with_seq = {
                "seq": seq,
                "chats": self.chats,
                "marker": self.marker
            }
            callback(payload_with_seq)

