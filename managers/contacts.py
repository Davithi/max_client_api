"""Модуль работы с контактами"""
from typing import List, Optional, Dict, Any
import asyncio
import logging
from ..models import Contact
from ..exceptions import ConnectionError
from ..packets.contacts import ResolvePhonePacket, ResolvePhoneAnswerPacket
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Utils.MaxUtils import MaxUtils

logger = logging.getLogger(__name__)

class ContactsManager:
    """Менеджер работы с контактами"""
    
    def __init__(self, asmax_client, connection):
        """
        Args:
            asmax_client: Экземпляр Asmax.Max.Client.MaxClient
            connection: Экземпляр Asmax.Max.Connection.MaxConnection
        """
        self._client = asmax_client
        self._connection = connection
        self._contacts_cache: Dict[int, Contact] = {}  # Кеш контактов по ID
        self._contacts_by_phone: Dict[str, Contact] = {}  # Кеш контактов по телефону
        self._auth_state: Optional[Dict[str, Any]] = None  # Полное состояние после авторизации
        
        # Для работы с resolve_phone
        self._pending_requests: Dict[int, asyncio.Future] = {}  # Словарь для хранения futures
        self._request_counter = 0  # Счётчик для seq
        
        # Регистрируем обработчик ответов
        self._register_resolve_phone_handler()
    
    def process_auth_state(self, auth_payload: Dict[str, Any]):
        """
        Обработать состояние авторизации и сохранить контакты в кеш
        
        Args:
            auth_payload: Полный payload из AuthTokenAnswerPacket (opcode 19, cmd=1)
        """
        self._auth_state = auth_payload
        
        # Парсим контакты из payload.contacts
        contacts_data = auth_payload.get('contacts', [])
        
        for contact_data in contacts_data:
            try:
                contact = Contact.from_dict(contact_data)
                if contact and contact.id:
                    self._contacts_cache[contact.id] = contact
                    # Также сохраняем по телефону для быстрого поиска
                    if contact.phone:
                        self._contacts_by_phone[contact.phone] = contact
            except Exception as e:
                logger.warning(f"Ошибка при парсинге контакта {contact_data.get('id')}: {e}")
        
        logger.info(f"Обработано {len(self._contacts_cache)} контактов из состояния авторизации")
    
    async def get_contacts(self, limit: int = 1000, offset: int = 0) -> List[Contact]:
        """
        Получить список всех контактов
        
        Args:
            limit: Максимальное количество контактов
            offset: Смещение для пагинации
        
        Returns:
            List[Contact]: Список контактов
        
        Note:
            Использует кеш из состояния авторизации (opcode 19).
            Если кеш пуст, возвращает пустой список.
        """
        # Возвращаем контакты из кеша
        contacts = list(self._contacts_cache.values())
        
        # Применяем offset и limit
        if offset > 0:
            contacts = contacts[offset:]
        if limit > 0:
            contacts = contacts[:limit]
        
        logger.info(f"Возвращено {len(contacts)} контактов (limit={limit}, offset={offset}, всего в кеше={len(self._contacts_cache)})")
        return contacts
    
    async def get_contact_by_id(self, contact_id: int) -> Optional[Contact]:
        """
        Получить контакт по ID
        
        Args:
            contact_id: ID контакта
        
        Returns:
            Contact или None если не найден
        """
        return self._contacts_cache.get(contact_id)
    
    async def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """
        Найти контакт по номеру телефона
        
        Args:
            phone: Номер телефона (с кодом страны или без)
        
        Returns:
            Contact или None если не найден
        """
        # Нормализуем телефон (убираем + и пробелы)
        normalized_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        # Прямой поиск
        if phone in self._contacts_by_phone:
            return self._contacts_by_phone[phone]
        
        if normalized_phone in self._contacts_by_phone:
            return self._contacts_by_phone[normalized_phone]
        
        # Поиск по частичному совпадению
        for stored_phone, contact in self._contacts_by_phone.items():
            stored_normalized = stored_phone.replace('+', '').replace(' ', '').replace('-', '')
            if stored_normalized == normalized_phone:
                return contact
        
        return None
    
    def _get_next_seq(self) -> int:
        """Получить следующий sequence number"""
        self._request_counter += 1
        return self._request_counter
    
    def _register_resolve_phone_handler(self):
        """Регистрирует обработчик ответов на запрос проверки номера"""
        def resolve_phone_callback(payload):
            """Callback для ответа на проверку номера (cmd=1, opcode=46)"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    # В payload есть поле "contact" с информацией о контакте
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на проверку номера (seq={seq})")
        
        # Регистрируем обработчик для opcode 46, cmd=1
        # Используем seq=-1, чтобы ловить все ответы с нужным opcode
        answer_header = PacketHeader(MaxUtils.global_ver, 1, -1, ResolvePhonePacket.OPCODE)
        self._connection.register_packet(
            answer_header,
            ResolvePhoneAnswerPacket,
            {"callback": resolve_phone_callback}
        )
    
    async def resolve_phone(self, phone: str) -> Optional[Contact]:
        """
        Проверить, зарегистрирован ли номер телефона в Max Messenger
        
        Args:
            phone: Номер телефона в формате +XXXXXXXXXX (например, "+37444971140")
        
        Returns:
            Optional[Contact]: Контакт, если номер зарегистрирован, иначе None
        
        Raises:
            ConnectionError: Если клиент не подключён
        """
        if not self._connection.conn.connected:
            raise ConnectionError("Соединение не установлено")
        
        # Получаем следующий seq
        seq = self._get_next_seq()
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос
            packet = ResolvePhonePacket(self._client.ws)
            packet.send_packet(phone, seq)
            
            logger.info(f"Отправлен запрос на проверку номера {phone} (seq={seq})")
            
            # Ждём ответа (таймаут 10 секунд)
            try:
                payload = await asyncio.wait_for(future, timeout=10.0)
                
                # Извлекаем contact из payload
                contact_data = payload.get("contact")
                
                if contact_data:
                    # Парсим контакт из ответа
                    contact = Contact.from_dict(contact_data)
                    logger.info(f"Номер {phone} зарегистрирован: {contact.name} (ID: {contact.id})")
                    
                    # Сохраняем в кеш
                    if contact.id:
                        self._contacts_cache[contact.id] = contact
                    if contact.phone:
                        self._contacts_by_phone[contact.phone] = contact
                    
                    return contact
                else:
                    logger.info(f"Номер {phone} не зарегистрирован в Max Messenger")
                    return None
                    
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут при проверке номера {phone} (seq={seq})")
                return None
            finally:
                # Удаляем из pending_requests
                self._pending_requests.pop(seq, None)
                
        except Exception as e:
            logger.error(f"Ошибка при проверке номера {phone}: {e}", exc_info=True)
            self._pending_requests.pop(seq, None)
            raise
