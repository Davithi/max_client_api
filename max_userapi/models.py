"""Модели данных для max_userapi"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class User:
    """Пользователь"""
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    
    @classmethod
    def from_asmax(cls, data: Any) -> 'User':
        """Создать из структуры Asmax"""
        if isinstance(data, dict):
            return cls(
                id=data.get('id', 0),
                name=data.get('name'),
                phone=data.get('phone'),
                username=data.get('username')
            )
        else:
            return cls(id=int(data) if data else 0)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создать из словаря"""
        return cls.from_asmax(data)


@dataclass
class Dialog:
    """Диалог/Чат"""
    id: int
    title: str
    is_group: bool = False
    unread_count: int = 0
    last_message: Optional['Message'] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Dialog':
        """Создать из словаря"""
        return cls(
            id=data.get('id', data.get('chatId', 0)),
            title=data.get('name', data.get('title', '')),
            is_group=data.get('type') == 'GROUP',
            unread_count=data.get('unreadCount', 0)
        )


@dataclass
class Chat:
    """Чат (группа или личный диалог)"""
    id: int
    title: str
    is_group: bool = False
    
    @classmethod
    def from_dialog(cls, dialog: Dialog) -> 'Chat':
        """Создать из Dialog"""
        return cls(
            id=dialog.id,
            title=dialog.title,
            is_group=dialog.is_group
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Chat':
        """Создать из словаря"""
        dialog = Dialog.from_dict(data)
        return cls.from_dialog(dialog)


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
            msg_date = datetime.fromtimestamp(timestamp)
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


@dataclass
class GroupInfo:
    """Информация о группе"""
    id: int
    title: str
    member_count: int
    member_ids: List[int]
    description: Optional[str] = None
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GroupInfo':
        """Создать из словаря"""
        return cls(
            id=data.get('id', data.get('chatId', 0)),
            title=data.get('title', data.get('name', '')),
            member_count=data.get('memberCount', data.get('membersCount', 0)),
            member_ids=data.get('memberIds', data.get('members', [])),
            description=data.get('description'),
            settings=data.get('settings', {})
        )


@dataclass
class Update:
    """Входящее обновление (новое сообщение и т.п.)"""
    type: str  # "message", "sticker", etc.
    message: Optional[Message] = None
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}

