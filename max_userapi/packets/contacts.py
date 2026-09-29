"""Пакеты для работы с контактами в Max Messenger"""
import websocket
from typing import Optional
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Packets.struct.AnswerPacket import AnswerPacket
from Asmax.Packets.struct.Packet import Packet


class ResolvePhonePacket(Packet):
    """
    Пакет для проверки/разрешения номера телефона (opcode 46)
    
    Проверяет, зарегистрирован ли номер в Max Messenger и возвращает информацию о контакте.
    """
    OPCODE = 46
    
    def __init__(self, ws: websocket.WebSocket):
        # seq будет установлен динамически при отправке
        super().__init__(PacketHeader(11, 0, -1, self.OPCODE))
        self.ws = ws
    
    def send_packet(self, phone: str, seq: int):
        """
        Отправить запрос на проверку номера телефона
        
        Args:
            phone: Номер телефона в формате +XXXXXXXXXX
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "phone": phone
        }
        
        # Устанавливаем seq в header
        self.header.seq = seq
        
        self.send(payload, self.ws)


class ResolvePhoneAnswerPacket(AnswerPacket):
    """
    Ответ на запрос проверки номера телефона (opcode 46, cmd=1)
    
    Содержит информацию о контакте, если номер зарегистрирован.
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.payload = payload
    
    def process(self, custom_data: dict):
        """
        Обработать ответ
        
        Args:
            custom_data: Словарь с ключом 'callback' (функция) для обработки результата
        """
        callback = custom_data.get('callback')
        if callback:
            # Передаём payload с seq для сопоставления
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)

