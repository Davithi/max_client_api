"""Модель пользователя"""
from dataclasses import dataclass
from typing import Optional, Any, List, Dict


@dataclass
class User:
    """Пользователь"""
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    account_status: Optional[int] = None  # Статус аккаунта
    
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
    
    @classmethod
    def from_profile_contact(cls, contact_data: dict) -> 'User':
        """
        Создать из profile.contact (из состояния авторизации)
        
        Args:
            contact_data: Данные из payload.profile.contact
        """
        # Обработка массива names
        names = contact_data.get('names', [])
        first_name = ""
        last_name = None
        full_name = None
        
        if names and len(names) > 0:
            # Берем первое имя (обычно это ONEME)
            name_data = names[0]
            first_name = name_data.get('firstName', name_data.get('name', ''))
            last_name = name_data.get('lastName')
            
            # Формируем полное имя
            if last_name:
                full_name = f"{first_name} {last_name}".strip()
            else:
                full_name = first_name
        
        # Если нет имени, используем телефон
        if not first_name:
            first_name = str(contact_data.get('phone', ''))
            full_name = first_name
        
        phone = contact_data.get('phone')
        if phone:
            phone = str(phone)
        
        return cls(
            id=contact_data.get('id', 0),
            name=full_name,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            account_status=contact_data.get('accountStatus')
        )

