"""Модели чата и диалога"""
from dataclasses import dataclass
from typing import Optional
from .message import Message


@dataclass
class Dialog:
    """Диалог/Чат"""
    id: int
    title: str
    is_group: bool = False
    unread_count: int = 0
    last_message: Optional[Message] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Dialog':
        """Создать из словаря"""
        # Тип чата может быть "CHAT" (группа) или "DIALOG" (личный диалог)
        chat_type = data.get('type', 'DIALOG')
        is_group = chat_type == 'CHAT'
        
        return cls(
            id=data.get('id', data.get('chatId', 0)),
            title=data.get('name', data.get('title', '')),
            is_group=is_group,
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

