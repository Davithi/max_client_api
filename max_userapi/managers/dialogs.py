"""Модуль работы с диалогами/чатами"""
from typing import List, Optional, Dict, Any
import logging
from ..models import Dialog, Message, Chat
from ..exceptions import ChatNotFoundError, ConnectionError

logger = logging.getLogger(__name__)


class DialogsManager:
    """Менеджер работы с диалогами"""
    
    def __init__(self, asmax_client, connection):
        """
        Args:
            asmax_client: Экземпляр Asmax.Max.Client.MaxClient
            connection: Экземпляр Asmax.Max.Connection.MaxConnection
        """
        self._client = asmax_client
        self._connection = connection
        self._chats_cache: Dict[int, Dialog] = {}
        self._auth_state: Optional[Dict[str, Any]] = None  # Полное состояние после авторизации
    
    def process_auth_state(self, auth_payload: Dict[str, Any]):
        """
        Обработать состояние авторизации и сохранить чаты в кеш
        
        Args:
            auth_payload: Полный payload из AuthTokenAnswerPacket (opcode 19, cmd=1)
        """
        self._auth_state = auth_payload
        
        # Парсим чаты из payload.chats
        chats_data = auth_payload.get('chats', [])
        
        for chat_data in chats_data:
            try:
                dialog = self._parse_chat_to_dialog(chat_data)
                if dialog:
                    self._chats_cache[dialog.id] = dialog
            except Exception as e:
                logger.warning(f"Ошибка при парсинге чата {chat_data.get('id')}: {e}")
        
        logger.info(f"Обработано {len(self._chats_cache)} чатов из состояния авторизации")
    
    def _parse_chat_to_dialog(self, chat_data: Dict[str, Any]) -> Optional[Dialog]:
        """
        Парсить данные чата в Dialog
        
        Args:
            chat_data: Данные чата из payload.chats
        
        Returns:
            Dialog или None если не удалось распарсить
        """
        chat_id = chat_data.get('id')
        if not chat_id:
            return None
        
        # Определяем тип чата
        chat_type = chat_data.get('type', 'DIALOG')
        is_group = chat_type == 'CHAT'
        
        # Получаем название
        title = chat_data.get('title', '')
        if not title:
            if is_group:
                # Для групп название обязательно должно быть
                title = f"Group {chat_id}"
            else:
                # Для диалогов название может быть в других полях или нужно получать из контактов
                # Пока используем ID как заглушку
                title = f"Chat {chat_id}"
        
        # Получаем количество участников для групп
        participants_count = chat_data.get('participantsCount', 0)
        if not participants_count and is_group:
            # Если нет participantsCount, считаем из participants
            participants = chat_data.get('participants', {})
            participants_count = len(participants) if isinstance(participants, dict) else 0
        
        # Создаём Dialog
        dialog = Dialog(
            id=chat_id,
            title=title,
            is_group=is_group,
            unread_count=0  # TODO: получить из chat_data если есть поле unread
        )
        
        return dialog
    
    async def get_dialogs(self, limit: int = 50, offset: int = 0) -> List[Dialog]:
        """
        Получить список всех чатов/диалогов
        
        Args:
            limit: Максимальное количество чатов
            offset: Смещение для пагинации
        
        Returns:
            List[Dialog]: Список диалогов
        
        Note:
            Использует кеш из состояния авторизации (opcode 19).
            Если кеш пуст, возвращает пустой список.
        """
        # Возвращаем чаты из кеша
        dialogs = list(self._chats_cache.values())
        
        # Применяем offset и limit
        if offset > 0:
            dialogs = dialogs[offset:]
        if limit > 0:
            dialogs = dialogs[:limit]
        
        logger.info(f"Возвращено {len(dialogs)} диалогов (limit={limit}, offset={offset}, всего в кеше={len(self._chats_cache)})")
        return dialogs
    
    async def get_chat(self, chat_id: int) -> Optional[Dialog]:
        """
        Получить информацию о чате по ID
        
        Args:
            chat_id: ID чата
        
        Returns:
            Dialog: Информация о чате или None если не найден
        
        Raises:
            ChatNotFoundError: Чат не найден
        """
        # Проверяем кеш
        if chat_id in self._chats_cache:
            return self._chats_cache[chat_id]
        
        # Если не в кеше, можно попробовать получить через GetChatInfoPacket
        # Но пока возвращаем None
        logger.warning(f"Чат {chat_id} не найден в кеше")
        return None
    
    async def get_chat_history(
        self,
        chat_id: int,
        limit: int = 50,
        before_message_id: Optional[str] = None
    ) -> List[Message]:
        """
        Получить историю сообщений чата
        
        Args:
            chat_id: ID чата
            limit: Количество сообщений
            before_message_id: ID сообщения, раньше которого загружать
        
        Returns:
            List[Message]: Список сообщений
        
        Raises:
            ChatNotFoundError: Чат не найден
        """
        # TODO: Реализовать через пакет GetChatHistoryPacket
        raise NotImplementedError("get_chat_history() требует исследования протокола")
    
    async def search_chats(self, query: str, limit: int = 50) -> List[Dialog]:
        """
        Поиск чатов
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
        
        Returns:
            List[Dialog]: Список найденных чатов
        """
        # TODO: Реализовать через пакет SearchChatsPacket
        raise NotImplementedError("search_chats() требует исследования протокола")

