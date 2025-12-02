"""Модель контакта"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class Contact:
    """Контакт"""
    id: int
    phone: str
    first_name: str
    last_name: Optional[str] = None
    name: Optional[str] = None  # Полное имя (first_name + last_name)
    photo_url: Optional[str] = None  # URL фото
    photo_id: Optional[int] = None  # ID фото
    description: Optional[str] = None  # Описание/статус
    update_time: Optional[int] = None  # Время последнего обновления
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Contact':
        """Создать из словаря (из payload.contacts)"""
        # Обработка массива names
        names = data.get('names', [])
        first_name = ""
        last_name = None
        full_name = None
        
        if names and len(names) > 0:
            # Предпочитаем ONEME имя, если есть, иначе берем первое
            name_data = None
            for n in names:
                if n.get('type') == 'ONEME':
                    name_data = n
                    break
            
            # Если ONEME не найден, берем первое имя
            if not name_data:
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
            first_name = str(data.get('phone', ''))
            full_name = first_name
        
        return cls(
            id=data.get('id', 0),
            phone=str(data.get('phone', '')),
            first_name=first_name,
            last_name=last_name,
            name=full_name,
            photo_url=data.get('baseUrl'),
            photo_id=data.get('photoId'),
            description=data.get('description'),
            update_time=data.get('updateTime')
        )

