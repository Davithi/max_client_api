"""Пакеты для обработки уведомлений от сервера Max Messenger"""
import logging
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Packets.struct.AnswerPacket import AnswerPacket


class TypingNotificationPacket(AnswerPacket):
    """
    Уведомление о наборе текста (opcode 129, cmd=0)
    
    Сервер отправляет это уведомление, когда пользователь начинает печатать в чате.
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat_id = payload.get("chatId")
        self.user_id = payload.get("userId")
        self.is_typing = payload.get("typing", True)  # True - печатает, False - перестал печатать
    
    def process(self, custom_data: dict):
        """Обработка уведомления о наборе текста"""
        callback = custom_data.get("callback")
        if callback:
            try:
                callback({
                    "chat_id": self.chat_id,
                    "user_id": self.user_id,
                    "is_typing": self.is_typing
                })
            except Exception as e:
                logging.warning(f"Ошибка при обработке уведомления о наборе текста: {e}")


class ChatUpdateNotificationPacket(AnswerPacket):
    """
    Уведомление об обновлении чата (opcode 135, cmd=0)
    
    Сервер отправляет это уведомление при изменениях в чате:
    - Изменение названия
    - Изменение описания
    - Изменение настроек
    - Изменение участников
    - И другие обновления
    """
    def __init__(self, header: PacketHeader, payload: dict):
        super().__init__(header, payload)
        self.chat = payload.get("chat", payload)  # Может быть объект чата или весь payload
        self.chat_id = self.chat.get("id") if isinstance(self.chat, dict) else payload.get("chatId")
    
    def process(self, custom_data: dict):
        """Обработка уведомления об обновлении чата"""
        callback = custom_data.get("callback")
        if callback:
            try:
                callback({
                    "chat": self.chat,
                    "chat_id": self.chat_id
                })
            except Exception as e:
                logging.warning(f"Ошибка при обработке уведомления об обновлении чата: {e}")

