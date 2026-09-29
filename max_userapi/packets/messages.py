"""Пакеты для работы с сообщениями в Max Messenger"""
import websocket
from typing import List
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Packets.struct.AnswerPacket import AnswerPacket
from Asmax.Packets.struct.Packet import Packet


class DeleteMessagePacket(Packet):
    """
    Пакет для удаления сообщения
    
    Использует opcode 66 (MSG_DELETE)
    """
    OPCODE = 66
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, 66))
        self.ws = ws
    
    def send_packet(self, chat_id: int, message_ids: List[str], for_me: bool, seq: int):
        """
        Удалить сообщение(я)
        
        Args:
            chat_id: ID чата
            message_ids: Список ID сообщений для удаления
            for_me: True - удалить только у себя, False - удалить у всех
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id,
            "messageIds": message_ids,
            "forMe": for_me
        }
        self.header.seq = seq
        self.send(payload, self.ws)


class DeleteMessageAnswerPacket(AnswerPacket):
    """Ответ на удаление сообщения (opcode 66, cmd=1)"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat_id = payload.get("chatId")
        self.message_ids = payload.get("messageIds", [])
    
    def process(self, custom_data: dict):
        """Обработка ответа на удаление сообщения"""
        seq = self.header.seq
        callback = custom_data.get("callback")
        
        if callback:
            payload_with_seq = {
                "seq": seq,
                "chatId": self.chat_id,
                "messageIds": self.message_ids
            }
            callback(payload_with_seq)


class EditMessagePacket(Packet):
    """
    Пакет для редактирования сообщения
    
    Использует opcode 67 (MSG_EDIT)
    """
    OPCODE = 67
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, 67))
        self.ws = ws
    
    def send_packet(self, chat_id: int, message_id: str, text: str, seq: int):
        """
        Отредактировать сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения для редактирования
            text: Новый текст сообщения
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id,
            "messageId": message_id,
            "text": text,
            "elements": [],
            "attachments": []
        }
        self.header.seq = seq
        self.send(payload, self.ws)


class EditMessageAnswerPacket(AnswerPacket):
    """Ответ на редактирование сообщения (opcode 67, cmd=1)"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.message = payload.get("message", {})
    
    def process(self, custom_data: dict):
        """Обработка ответа на редактирование сообщения"""
        seq = self.header.seq
        callback = custom_data.get("callback")
        
        if callback:
            payload_with_seq = {
                "seq": seq,
                "message": self.message
            }
            callback(payload_with_seq)

