"""Модель информации о группе"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class GroupInfo:
    """Информация о группе"""
    id: int
    title: str
    member_count: int
    member_ids: List[int]
    description: Optional[str] = None
    settings: Dict[str, Any] = None
    invite_link: Optional[str] = None  # Приватная ссылка для приглашения
    
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
            settings=data.get('settings', {}),
            invite_link=data.get('link')  # Парсим ссылку из ответа
        )

