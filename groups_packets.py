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
    
    Создание группы происходит через отправку сообщения (opcode 64) с CONTROL attach.
    Структура основана на анализе WebSocket трафика при создании группы через веб-интерфейс.
    """
    def __init__(self, ws: websocket.WebSocket):
        # Используем opcode 64 (SendMessage) для создания группы через CONTROL сообщение
        # seq будет установлен динамически при отправке, используем -1 как placeholder
        super().__init__(PacketHeader(11, 0, -1, 64))
        self.ws = ws
    
    def send_packet(self, title: str, member_ids: List[int], seq: int, description: Optional[str] = None):
        """
        Отправить запрос на создание группы
        
        Args:
            title: Название группы
            member_ids: Список ID участников
            seq: Sequence number для сопоставления запроса и ответа
            description: Описание группы (опционально, пока не используется)
        """
        from Asmax.Utils.MaxUtils import MaxUtils
        
        # Структура точно соответствует WebSocket трафику браузера
        # CONTROL attach с chatType: "CHAT"
        control_attach = {
            "_type": "CONTROL",
            "event": "new",
            "chatType": "CHAT",
            "title": title,
            "userIds": member_ids  # Всегда включаем, даже если пустой список
        }
        
        # Payload без chatId на верхнем уровне
        # notify: true (как в браузере)
        payload = {
            "message": {
                "cid": MaxUtils.get_timestamp(),
                "attaches": [control_attach]
            },
            "notify": True
        }
        
        # Устанавливаем seq в header
        self.header.seq = seq
        
        # Логируем отправляемый пакет для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Отправка пакета создания группы (seq={seq}): {payload}")
        
        self.send(payload, self.ws)


class CreateGroupAnswerPacket(AnswerPacket):
    """
    Ответ на создание группы (cmd=1, opcode=64)
    
    Структура ответа:
    {
        "chatId": <new_chat_id>,
        "message": {...},
        "unread": 0,
        "chat": {... полный объект чата ...},
        "mark": <timestamp>
    }
    """
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat_id = payload.get("chatId")
        self.chat_info = payload.get("chat", payload)
        self.message = payload.get("message")
        self.unread = payload.get("unread", 0)
        self.mark = payload.get("mark")
    
    def process(self, custom_data: dict):
        """Обработка ответа - передаём весь payload в callback"""
        callback = custom_data.get("callback")
        if callback:
            # Передаём весь payload с seq для сопоставления
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
    
    Добавление участников происходит через отправку сообщения (opcode 64) с CONTROL attach.
    Структура основана на анализе WebSocket трафика при добавлении участников через веб-интерфейс.
    """
    OPCODE = 64  # Используем SendMessage
    
    def __init__(self, ws: websocket.WebSocket):
        # Используем opcode 64 (SendMessage) для добавления участников через CONTROL сообщение
        # seq будет установлен динамически при отправке, используем -1 как placeholder
        super().__init__(PacketHeader(11, 0, -1, 64))
        self.ws = ws
    
    def send_packet(self, chat_id: int, member_ids: List[int], seq: int):
        """
        Отправить запрос на добавление участников в группу
        
        Args:
            chat_id: ID группы
            member_ids: Список ID участников для добавления
            seq: Sequence number для сопоставления запроса и ответа
        """
        from Asmax.Utils.MaxUtils import MaxUtils
        
        # Структура точно соответствует WebSocket трафику браузера
        # CONTROL attach с event: "add"
        control_attach = {
            "_type": "CONTROL",
            "event": "add",
            "userIds": member_ids
        }
        
        # Payload как в SendMessage
        payload = {
            "chatId": chat_id,
            "message": {
                "cid": MaxUtils.get_timestamp(),
                "attaches": [control_attach]
            },
            "notify": True
        }
        
        # Устанавливаем seq в header
        self.header.seq = seq
        
        # Логируем отправляемый пакет для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Отправка пакета добавления участников (seq={seq}): {payload}")
        
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

