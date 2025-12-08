"""Модуль работы с диалогами/чатами"""
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
from ..models import Dialog, Message, Chat
from ..exceptions import ChatNotFoundError, ConnectionError
from ..packets.dialogs import (
    GetChatHistoryPacket,
    GetChatHistoryAnswerPacket,
    GetChatsListPacket,
    GetChatsListAnswerPacket,
)
from Asmax.Packets.struct.PacketHeader import PacketHeader
from Asmax.Utils.MaxUtils import MaxUtils

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
        self._chat_marker: Optional[int] = None  # chatMarker из ответа opcode 19
        self._all_dialogs_fetched: bool = False  # Флаг, что все чаты уже получены через opcode 53
        
        # Словарь для хранения futures для ожидания ответов
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._request_counter = 0
        
        # Регистрируем обработчики ответов
        self._register_answer_handlers()
    
    def _get_next_seq(self) -> int:
        """Получить следующий sequence number"""
        self._request_counter += 1
        return self._request_counter
    
    def _register_answer_handlers(self):
        """Регистрирует обработчики ответов от сервера"""
        def get_chat_history_callback(payload):
            """Callback для ответа на получение истории чата (cmd=1, opcode=49)"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на получение истории чата (seq={seq})")
        
        def get_chats_list_callback(payload):
            """Callback для ответа на получение списка чатов (cmd=1, opcode=53)"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на получение списка чатов (seq={seq})")
        
        # Регистрируем пакет ответа для истории чата
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 49),
            GetChatHistoryAnswerPacket,
            {"callback": get_chat_history_callback}
        )
        
        # Регистрируем пакет ответа для списка чатов
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 53),
            GetChatsListAnswerPacket,
            {"callback": get_chats_list_callback}
        )
    
    def process_auth_state(self, auth_payload: Dict[str, Any]):
        """
        Обработать состояние авторизации и сохранить чаты в кеш
        
        Args:
            auth_payload: Полный payload из AuthTokenAnswerPacket (opcode 19, cmd=1)
        """
        self._auth_state = auth_payload
        
        # Сохраняем chatMarker из ответа opcode 19 для использования в первом запросе opcode 53
        self._chat_marker = auth_payload.get('chatMarker')
        if self._chat_marker:
            logger.info(f"Сохранён chatMarker из opcode 19: {self._chat_marker}")
        else:
            logger.warning("chatMarker не найден в ответе opcode 19")
        
        # Сбрасываем флаг получения всех чатов (новый логин = нужно обновить данные)
        self._all_dialogs_fetched = False
        
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
    
    async def get_dialogs(self, limit: int = 10000, offset: int = 0) -> List[Dialog]:
        """
        Получить список всех чатов/диалогов
        
        Логика:
        1. Сразу возвращает данные из кеша (opcode 19) для быстрого отображения
        2. Параллельно запрашивает opcode 53 для получения всех чатов
        3. Объединяет результаты (убирает дубликаты по ID) и возвращает полный список
        
        Args:
            limit: Максимальное количество чатов (0 = без ограничений)
            offset: Смещение для пагинации
        
        Returns:
            List[Dialog]: Список диалогов (сначала из кеша, потом дополняется данными из opcode 53)
        """
        # 1. Сразу возвращаем данные из кеша (opcode 19) - быстро
        cache_dialogs = self._get_dialogs_from_cache(limit=limit, offset=offset)
        logger.info(f"📋 Сразу возвращаем {len(cache_dialogs)} чатов из кеша (opcode 19)")
        
        # 2. Проверяем, были ли уже получены все чаты через opcode 53
        if self._all_dialogs_fetched:
            logger.debug("✅ Все чаты уже получены через opcode 53, используем только кеш")
            # Применяем limit/offset к кешу
            all_dialogs = list(self._chats_cache.values())
            all_dialogs.sort(key=lambda d: d.id)
            if offset > 0:
                all_dialogs = all_dialogs[offset:]
            if limit > 0:
                all_dialogs = all_dialogs[:limit]
            return all_dialogs
        
        # 3. Если ещё не получали все чаты, запрашиваем opcode 53 для получения всех чатов
        try:
            api_dialogs = await self._get_all_dialogs_from_api(limit=limit, offset=offset)
            if api_dialogs:
                logger.info(f"✅ Получено {len(api_dialogs)} чатов через opcode 53")
                
                # 4. Объединяем результаты: создаем словарь по ID для быстрого поиска
                dialogs_dict = {d.id: d for d in cache_dialogs}
                
                # Добавляем чаты из opcode 53 (они перезапишут дубликаты из кеша)
                for dialog in api_dialogs:
                    dialogs_dict[dialog.id] = dialog
                
                # Обновляем кеш данными из opcode 53
                for dialog in api_dialogs:
                    self._chats_cache[dialog.id] = dialog
                
                # Устанавливаем флаг, что все чаты получены
                self._all_dialogs_fetched = True
                logger.info("✅ Флаг _all_dialogs_fetched установлен в True - повторные запросы opcode 53 не нужны")
                
                # Преобразуем обратно в список и применяем limit/offset
                all_dialogs = list(dialogs_dict.values())
                
                # Сортируем по ID для консистентности (или можно по другому критерию)
                all_dialogs.sort(key=lambda d: d.id)
                
                if offset > 0:
                    all_dialogs = all_dialogs[offset:]
                if limit > 0:
                    all_dialogs = all_dialogs[:limit]
                
                logger.info(f"📊 Итого: {len(cache_dialogs)} из кеша + {len(api_dialogs)} из API = {len(all_dialogs)} уникальных чатов")
                return all_dialogs
            else:
                logger.warning("⚠️ Opcode 53 вернул пустой список, используем только кеш")
                return cache_dialogs
        except (ConnectionError, asyncio.TimeoutError) as e:
            logger.warning(f"⚠️ Opcode 53 не работает ({type(e).__name__}: {e}), используем только кеш из opcode 19")
            return cache_dialogs
        except Exception as e:
            logger.error(f"❌ Ошибка при получении чатов через opcode 53: {e}, используем только кеш")
            return cache_dialogs
    
    def _get_dialogs_from_cache(self, limit: int = 10000, offset: int = 0) -> List[Dialog]:
        """
        Получить чаты из кеша (opcode 19)
        
        Args:
            limit: Максимальное количество чатов
            offset: Смещение для пагинации
        
        Returns:
            List[Dialog]: Список диалогов из кеша
        """
        dialogs = list(self._chats_cache.values())
        
        # Применяем offset и limit
        if offset > 0:
            dialogs = dialogs[offset:]
        if limit > 0:
            dialogs = dialogs[:limit]
        
        logger.info(f"Возвращено {len(dialogs)} диалогов из кеша (limit={limit}, offset={offset}, всего в кеше={len(self._chats_cache)})")
        return dialogs
    
    async def _get_all_dialogs_from_api(self, limit: int = 10000, offset: int = 0) -> List[Dialog]:
        """
        Получить все чаты через opcode 53 (CHATS_LIST) с пагинацией
        
        Args:
            limit: Максимальное количество чатов (0 = без ограничений)
            offset: Смещение для пагинации
        
        Returns:
            List[Dialog]: Список всех диалогов
        
        Raises:
            ConnectionError: Клиент не подключён или ошибка при получении данных
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Проверяем, что у нас есть chatMarker из opcode 19
        if not self._chat_marker:
            logger.warning("chatMarker не найден, невозможно выполнить запрос opcode 53")
            raise ConnectionError("chatMarker не найден в ответе opcode 19")
        
        all_dialogs: List[Dialog] = []
        # Для первого запроса используем chatMarker из opcode 19
        marker = self._chat_marker
        page_number = 0
        
        logger.info(f"Начинаем получение всех чатов через opcode 53 (начальный marker={marker})...")
        
        while True:
            page_number += 1
            # Создаём Future для ожидания ответа
            future = asyncio.Future()
            seq = self._get_next_seq()
            self._pending_requests[seq] = future
            
            try:
                # Отправляем запрос (без limit, только marker)
                packet = GetChatsListPacket(self._client.ws)
                packet.send_packet(marker=marker, seq=seq)
                
                logger.info(f"📤 Отправлен запрос на получение списка чатов (страница {page_number}, seq={seq}, marker={marker})")
                
                # Ждём ответ
                try:
                    response = await asyncio.wait_for(future, timeout=10.0)
                    chats_data = response.get("chats", [])
                    marker = response.get("marker")
                    
                    if not chats_data:
                        logger.warning(f"Получен пустой список чатов на странице {page_number}")
                        # Если это первая страница и она пустая, это может быть ошибка
                        if page_number == 1:
                            logger.error("Первая страница пустая - возможно, opcode 53 не работает")
                            raise ConnectionError("Opcode 53 вернул пустой список на первой странице")
                        # Если не первая страница, просто завершаем
                        break
                    
                    # Парсим чаты
                    parsed_count = 0
                    for chat_data in chats_data:
                        try:
                            dialog = self._parse_chat_to_dialog(chat_data)
                            if dialog:
                                all_dialogs.append(dialog)
                                parsed_count += 1
                        except Exception as e:
                            logger.warning(f"Ошибка при парсинге чата {chat_data.get('id')}: {e}")
                    
                    logger.info(f"Страница {page_number}: получено {len(chats_data)} чатов, распарсено {parsed_count}, всего собрано: {len(all_dialogs)}")
                    
                    # Проверяем окончание пагинации: если marker == 0 (int или str), значит это последняя страница
                    if marker is None or marker == 0 or marker == "0" or (isinstance(marker, str) and marker.strip() == "0"):
                        logger.info(f"Достигнута последняя страница (marker={marker})")
                        break
                    
                    # Если достигнут лимит, останавливаемся
                    if limit > 0 and len(all_dialogs) >= limit:
                        logger.info(f"Достигнут лимит {limit}, остановка пагинации")
                        break
                    
                    # Задержка между запросами (3 секунды)
                    await asyncio.sleep(3.0)
                        
                except asyncio.TimeoutError:
                    logger.error(f"Таймаут ожидания ответа при получении списка чатов (страница {page_number})")
                    if page_number == 1:
                        # Если таймаут на первой странице, это критическая ошибка
                        raise ConnectionError("Таймаут при получении списка чатов через opcode 53")
                    # Если таймаут на последующих страницах, просто останавливаемся
                    logger.warning("Таймаут на последующих страницах, возвращаем то, что успели получить")
                    break
                    
            finally:
                self._pending_requests.pop(seq, None)
        
        # Применяем offset и limit
        if offset > 0:
            all_dialogs = all_dialogs[offset:]
        if limit > 0:
            all_dialogs = all_dialogs[:limit]
        
        logger.info(f"Всего получено {len(all_dialogs)} диалогов через API (limit={limit}, offset={offset}, страниц={page_number})")
        return all_dialogs
    
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
        backward: int = 30,
        forward: int = 0,
        before_message_id: Optional[str] = None,
        from_timestamp: Optional[int] = None
    ) -> List[Message]:
        """
        Получить историю сообщений чата
        
        Args:
            chat_id: ID чата
            backward: Количество сообщений назад (по умолчанию 30)
            forward: Количество сообщений вперед (по умолчанию 0 для пагинации в прошлое)
            before_message_id: ID сообщения, раньше которого загружать (опционально, для пагинации)
            from_timestamp: Timestamp сообщения для пагинации (опционально, вместо before_message_id)
        
        Returns:
            List[Message]: Список сообщений
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Проверяем, что соединение активно
        if not hasattr(self._client.ws, 'connected') or not self._client.ws.connected:
            raise ConnectionError("Соединение закрыто")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Если указан before_message_id, нужно сначала получить timestamp этого сообщения
            # Но пока используем from_timestamp напрямую, если передан
            # Если передан before_message_id, можно использовать его как from_timestamp
            # (но это требует дополнительного запроса, пока не реализовано)
            
            # Отправляем запрос
            packet = GetChatHistoryPacket(self._client.ws)
            packet.send_packet(
                chat_id=chat_id,
                backward=backward,  # Используем переданное значение
                forward=forward,   # Используем переданное значение
                from_timestamp=from_timestamp,
                seq=seq
            )
            
            logger.info(f"Отправлен запрос на получение истории чата {chat_id} (seq={seq}, backward={backward}, forward={forward}, from_timestamp={from_timestamp})")
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Логируем полный ответ от сервера для отладки
                logger.debug(f"Полный ответ от сервера для чата {chat_id} (seq={seq}): {response}")
                
                # Парсим сообщения из ответа
                messages_data = response.get("messages", [])
                if not messages_data:
                    logger.debug(f"Ответ не содержит поле 'messages' или оно пустое. Структура ответа: {list(response.keys())}")
                messages = []
                
                for msg_data in messages_data:
                    try:
                        # Парсим timestamp
                        timestamp = msg_data.get("time", 0)
                        if timestamp:
                            msg_date = datetime.fromtimestamp(timestamp / 1000)
                        else:
                            msg_date = datetime.now()
                        
                        # Парсим sender
                        sender_id = msg_data.get("sender", 0)
                        if isinstance(sender_id, dict):
                            sender_id = sender_id.get('id', 0)
                        
                        # Парсим текст
                        text = msg_data.get("text", "")
                        
                        # Парсим ID
                        message_id = str(msg_data.get("id", ""))
                        
                        # Создаём Message с сохранением исходных данных
                        message = Message(
                            id=message_id,
                            chat_id=chat_id,
                            sender_id=sender_id,
                            text=text,
                            date=msg_date
                        )
                        
                        # Сохраняем полные исходные данные в атрибуте для доступа через бекенд
                        message._raw_data = msg_data
                        
                        messages.append(message)
                    except Exception as e:
                        logger.warning(f"Ошибка при парсинге сообщения: {e}")
                        continue
                
                logger.info(f"Получено {len(messages)} сообщений из чата {chat_id}")
                return messages
                
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при получении истории чата")
                raise ConnectionError("Таймаут при получении истории чата")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def search_chats(self, query: str, limit: int = 10000) -> List[Dialog]:
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

