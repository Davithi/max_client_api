"""Модель информации о группе"""
from dataclasses import dataclass, field
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
    owner: Optional[int] = None  # ID владельца группы
    admins: List[int] = field(default_factory=list)  # Список ID админов группы
    _raw_data: Optional[Dict[str, Any]] = None  # Полные raw данные для доступа к дополнительным полям
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}
        if self.admins is None:
            self.admins = []
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GroupInfo':
        """Создать из словаря"""
        # Парсим owner
        owner = data.get('owner')
        if owner is None:
            owner = None
        elif isinstance(owner, dict):
            owner = owner.get('id')
        elif isinstance(owner, (int, str)):
            owner = int(owner)
        
        # Парсим admins
        admins = []
        if 'admins' in data and isinstance(data['admins'], list):
            admins = [int(admin) if isinstance(admin, (int, str)) else admin for admin in data['admins']]
        elif 'adminParticipants' in data and isinstance(data['adminParticipants'], dict):
            # adminParticipants может быть словарём {id: {id: ...}}
            admins = [int(admin_id) for admin_id in data['adminParticipants'].keys() if admin_id]
        
        # Парсим member_ids из participants если нужно
        member_ids = data.get('memberIds', data.get('members', []))
        if not member_ids and 'participants' in data:
            participants = data.get('participants', {})
            if isinstance(participants, dict):
                member_ids = [int(pid) for pid in participants.keys() if pid]
            elif isinstance(participants, list):
                member_ids = participants
        
        return cls(
            id=data.get('id', data.get('chatId', 0)),
            title=data.get('title', data.get('name', '')),
            member_count=data.get('memberCount', data.get('membersCount', data.get('participantsCount', 0))),
            member_ids=member_ids if isinstance(member_ids, list) else [],
            description=data.get('description'),
            settings=data.get('settings', {}),
            invite_link=data.get('link'),  # Парсим ссылку из ответа
            owner=owner,
            admins=admins,
            _raw_data=data.copy()  # Сохраняем полные raw данные
        )

