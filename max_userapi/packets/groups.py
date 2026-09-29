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
    
    Использует opcode 77 (CHAT_MEMBERS_UPDATE) с operation: "add"
    """
    OPCODE = 77  # CHAT_MEMBERS_UPDATE
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, 77))
        self.ws = ws
    
    def send_packet(self, chat_id: int, member_ids: List[int], seq: int):
        """
        Отправить запрос на добавление участников в группу
        
        Args:
            chat_id: ID группы
            member_ids: Список ID участников для добавления
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id,
            "userIds": member_ids,
            "operation": "add",
            "cleanMsgPeriod": 0
        }
        self.header.seq = seq
        self.send(payload, self.ws)


class AddGroupMembersAnswerPacket(AnswerPacket):
    """Ответ на добавление участников (opcode 77, cmd=1)"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat = payload.get("chat")
    
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
    
    Использует opcode 77 (CHAT_MEMBERS_UPDATE) с operation: "remove"
    """
    OPCODE = 77  # CHAT_MEMBERS_UPDATE
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, 77))
        self.ws = ws
    
    def send_packet(self, chat_id: int, member_ids: List[int], seq: int):
        """
        Удалить участников из группы
        
        Args:
            chat_id: ID группы
            member_ids: Список ID пользователей для удаления
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id,
            "userIds": member_ids,  # ВАЖНО: userIds, а не memberIds
            "operation": "remove",
            "cleanMsgPeriod": 0
        }
        self.header.seq = seq
        self.send(payload, self.ws)


class RemoveGroupMembersAnswerPacket(AnswerPacket):
    """Ответ на удаление участников (opcode 77, cmd=1)"""
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat = payload.get("chat")
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class LeaveGroupPacket(Packet):
    """
    Пакет для выхода из группы
    
    Использует opcode 58 (CHAT_LEAVE)
    """
    OPCODE = 58  # CHAT_LEAVE
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, self.OPCODE))
        self.ws = ws
    
    def send_packet(self, chat_id: int, seq: int):
        """
        Отправить запрос на выход из группы
        
        Args:
            chat_id: ID группы
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id
        }
        
        self.header.seq = seq
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Отправка пакета выхода из группы (seq={seq}): {payload}")
        
        self.send(payload, self.ws)


class LeaveGroupAnswerPacket(AnswerPacket):
    """
    Ответ на выход из группы (opcode 58, cmd=1)
    
    Содержит обновлённую информацию о чате или подтверждение выхода.
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.payload = payload
    
    def process(self, custom_data: dict):
        """Обработка ответа - передаём весь payload в callback"""
        callback = custom_data.get("callback")
        if callback:
            # Передаём весь payload с seq для сопоставления
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class GetAuthStatePacket(Packet):
    """
    Пакет для получения состояния авторизации с токеном (opcode 19)
    
    Используется для получения полного списка чатов, включая группы с полной информацией.
    """
    OPCODE = 19
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, self.OPCODE))
        self.ws = ws
    
    def send_packet(self, token: str, interactive: bool = True, chats_count: int = 40, seq: int = -1):
        """
        Запросить состояние авторизации с токеном
        
        Args:
            token: Токен авторизации
            interactive: Интерактивный режим (по умолчанию True)
            chats_count: Количество чатов для синхронизации
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "interactive": interactive,
            "token": token,
            "chatsCount": chats_count,
            "chatsSync": 0,
            "contactsSync": 0,
            "presenceSync": 0,
            "draftsSync": 0
        }
        self.header.seq = seq
        self.send(payload, self.ws)


class GetChatInfoPacket(Packet):
    """
    Пакет для получения информации о чате/группе
    
    Использует opcode 48 (CHAT_INFO) согласно документации.
    Также поддерживает opcode 69 для обратной совместимости.
    """
    OPCODE_48 = 48  # CHAT_INFO (основной)
    OPCODE_69 = 69  # Альтернативный (для обратной совместимости)
    
    def __init__(self, ws: websocket.WebSocket, use_opcode_48: bool = True):
        """
        Args:
            ws: WebSocket соединение
            use_opcode_48: Если True - использует opcode 48, иначе opcode 69
        """
        opcode = self.OPCODE_48 if use_opcode_48 else self.OPCODE_69
        super().__init__(PacketHeader(11, 0, -1, opcode))
        self.ws = ws
        self.use_opcode_48 = use_opcode_48
    
    def send_packet(self, chat_id: int, seq: int = 0):
        """
        Запросить информацию о чате
        
        Args:
            chat_id: ID чата
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id
        }
        self.header.seq = seq
        self.send(payload, self.ws)


class GetChatInfoAnswerPacket(AnswerPacket):
    """
    Ответ с информацией о чате (opcode 48 или 69, cmd=1)
    
    Может приходить как ответ на GetChatInfoPacket (opcode 48 или 69).
    """
    
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat_info = payload.get("chat", payload)
    
    def process(self, custom_data: dict):
        """Обработка ответа"""
        callback = custom_data.get("callback")
        if callback:
            # Добавляем seq из header для сопоставления запроса и ответа
            payload_with_seq = {
                "seq": self.header.seq,
                "chat": self.chat_info
            }
            callback(payload_with_seq)
            # Добавляем seq из header
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class UpdateGroupOptionsPacket(Packet):
    """
    Пакет для изменения настроек (опций) группы (opcode 55)
    
    Используется для управления разрешениями участников, изменения названия, описания и получения ссылки:
    - ONLY_OWNER_CAN_CHANGE_ICON_TITLE - только владелец может менять название, фото и описание
    - ONLY_ADMIN_CAN_ADD_MEMBER - только админы могут добавлять участников
    - ONLY_ADMIN_CAN_CALL - только админы могут звонить
    - ALL_CAN_PIN_MESSAGE - все могут закреплять сообщения
    - theme - изменение названия группы
    - description - изменение описания группы
    - revokePrivateLink - получение/обновление приватной ссылки группы
    - и другие опции
    """
    OPCODE = 55
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, self.OPCODE))
        self.ws = ws
    
    def send_packet(self, chat_id: int, options: Optional[Dict[str, Any]] = None, theme: Optional[str] = None, description: Optional[str] = None, revoke_private_link: Optional[bool] = None, seq: int = -1):
        """
        Отправить запрос на изменение опций группы, названия, описания или получение ссылки
        
        Args:
            chat_id: ID группы
            options: Словарь с опциями (например, {"ONLY_OWNER_CAN_CHANGE_ICON_TITLE": True})
            theme: Новое название группы
            description: Новое описание группы
            revoke_private_link: True - получить/обновить приватную ссылку группы
            seq: Sequence number для сопоставления запроса и ответа
        """
        payload = {
            "chatId": chat_id
        }
        
        if theme is not None:
            payload["theme"] = theme
        elif description is not None:
            payload["description"] = description
        elif revoke_private_link is not None:
            payload["revokePrivateLink"] = revoke_private_link
        elif options is not None:
            payload["options"] = options
        else:
            raise ValueError("Необходимо указать либо options, либо theme, либо description, либо revoke_private_link")
        
        # Устанавливаем seq в header
        self.header.seq = seq
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Отправка пакета изменения опций/названия/описания/ссылки группы (seq={seq}): {payload}")
        
        self.send(payload, self.ws)


class UpdateGroupOptionsAnswerPacket(AnswerPacket):
    """
    Ответ на изменение опций группы (opcode 55, cmd=1)
    
    Содержит полный объект чата с обновленными опциями.
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.payload = payload
    
    def process(self, custom_data: dict):
        """Обработка ответа - передаём весь payload в callback"""
        callback = custom_data.get("callback")
        if callback:
            # Передаём весь payload с seq для сопоставления
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class JoinGroupByLinkPacket(Packet):
    """
    Пакет для присоединения к группе по ссылке-приглашению
    
    Использует opcode 57 (CHAT_JOIN)
    """
    OPCODE = 57  # CHAT_JOIN
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, self.OPCODE))
        self.ws = ws
    
    def send_packet(self, link: str, seq: int):
        """
        Отправить запрос на присоединение к группе по ссылке
        
        Args:
            link: Ссылка на группу (может быть полной "https://max.ru/join/..." 
                  или только частью "join/...")
            seq: Sequence number для сопоставления запроса и ответа
        """
        # Если передана полная ссылка, извлекаем только часть после max.ru/
        if link.startswith("http"):
            # Извлекаем часть после max.ru/
            if "max.ru/" in link:
                link = link.split("max.ru/", 1)[1]
            elif "max.ru" in link:
                link = link.split("max.ru", 1)[1].lstrip("/")
        
        # Убираем начальный слэш, если есть
        link = link.lstrip("/")
        
        payload = {
            "link": link
        }
        
        self.header.seq = seq
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Отправка пакета присоединения к группе по ссылке (seq={seq}): {payload}")
        
        self.send(payload, self.ws)


class JoinGroupByLinkAnswerPacket(AnswerPacket):
    """
    Ответ на присоединение к группе по ссылке (opcode 57, cmd=1)
    
    Содержит полный объект чата с информацией о группе.
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.payload = payload
    
    def process(self, custom_data: dict):
        """Обработка ответа - передаём весь payload в callback"""
        callback = custom_data.get("callback")
        if callback:
            # Передаём весь payload с seq для сопоставления
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)


class GetGroupPreviewByLinkPacket(Packet):
    """
    Пакет для получения preview информации о группе по ссылке-приглашению
    (без фактического присоединения)
    
    Использует opcode 89
    """
    OPCODE = 89
    
    def __init__(self, ws: websocket.WebSocket):
        super().__init__(PacketHeader(11, 0, -1, self.OPCODE))
        self.ws = ws
    
    def send_packet(self, link: str, seq: int):
        """
        Отправить запрос на получение preview информации о группе по ссылке
        
        Args:
            link: Ссылка на группу (может быть полной "https://max.ru/join/..." 
                  или только частью "join/...")
            seq: Sequence number для сопоставления запроса и ответа
        """
        # Если передана полная ссылка, извлекаем только часть после max.ru/
        if link.startswith("http"):
            if "max.ru/" in link:
                link = link.split("max.ru/", 1)[1]
            elif "max.ru" in link:
                link = link.split("max.ru", 1)[1].lstrip("/")
        
        # Убираем начальный слэш, если есть
        link = link.lstrip("/")
        
        payload = {
            "link": link
        }
        
        self.header.seq = seq
        
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Отправка пакета preview группы по ссылке (seq={seq}): {payload}")
        
        self.send(payload, self.ws)


class GetGroupPreviewByLinkAnswerPacket(AnswerPacket):
    """
    Ответ на запрос preview информации о группе по ссылке (opcode 89, cmd=1)
    
    Содержит полный объект чата с информацией о группе (без присоединения).
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.payload = payload
    
    def process(self, custom_data: dict):
        """Обработка ответа - передаём весь payload в callback"""
        callback = custom_data.get("callback")
        if callback:
            # Передаём весь payload с seq для сопоставления
            payload_with_seq = self.payload.copy()
            payload_with_seq["seq"] = self.header.seq
            callback(payload_with_seq)

