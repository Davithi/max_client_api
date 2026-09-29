"""Модель сообщения"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    """Сообщение"""
    id: str
    chat_id: int
    sender_id: int
    text: str
    date: datetime
    is_reply: bool = False
    reply_to_id: Optional[str] = None
    
    @classmethod
    def from_asmax(cls, asmax_msg) -> 'Message':
        """Создать из Asmax.Packets.ReceiveMessage.Message"""
        sender_id = asmax_msg.sender
        if isinstance(sender_id, dict):
            sender_id = sender_id.get('id', 0)
        
        timestamp = asmax_msg.time
        if timestamp:
            # Проверяем формат timestamp
            # Если timestamp в миллисекундах (больше чем разумный timestamp в секундах)
            if timestamp > 1e10:  # Больше чем timestamp для 2000 года в миллисекундах
                # Это миллисекунды, конвертируем в секунды
                try:
                    msg_date = datetime.fromtimestamp(timestamp / 1000)
                except (ValueError, OSError):
                    msg_date = datetime.now()
            elif timestamp < 946684800:  # Меньше чем timestamp для 2000-01-01
                # Некорректный timestamp, используем текущее время
                msg_date = datetime.now()
            else:
                # Это секунды
                try:
                    msg_date = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError):
                    # Если не удалось создать datetime, используем текущее время
                    msg_date = datetime.now()
        else:
            msg_date = datetime.now()
        
        reply_to_id = None
        is_reply = asmax_msg.is_reply
        if is_reply and hasattr(asmax_msg, 'link') and asmax_msg.link:
            if hasattr(asmax_msg.link, 'message'):
                reply_to_id = asmax_msg.link.message.id if hasattr(asmax_msg.link.message, 'id') else None
        
        return cls(
            id=str(asmax_msg.id),
            chat_id=asmax_msg.chatId,
            sender_id=sender_id,
            text=asmax_msg.text or '',
            date=msg_date,
            is_reply=is_reply,
            reply_to_id=reply_to_id
        )

