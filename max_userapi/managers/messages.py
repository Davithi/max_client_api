"""Модуль работы с сообщениями"""
from datetime import datetime
from typing import List, Callable, Awaitable, Dict
import asyncio
import logging
from ..models import Message
from ..exceptions import ConnectionError
from ..packets.messages import (
    DeleteMessagePacket,
    DeleteMessageAnswerPacket,
    EditMessagePacket,
    EditMessageAnswerPacket,
)
from Asmax.Packets.struct.PacketHeader import PacketHeader

# Импорт из Asmax
from Asmax.Packets.SendMessage import (
    SendMessagePacket,
    SendReplyMessagePacket,
    SendStickerPacket,
    SendReplyStickerPacket
)
from Asmax.Packets.ReceiveMessage import Message as AsmaxMessage

logger = logging.getLogger(__name__)


class MessagesManager:
    """Менеджер работы с сообщениями"""
    
    def __init__(self, asmax_client, connection):
        """
        Args:
            asmax_client: Экземпляр Asmax.Max.Client.MaxClient
            connection: Экземпляр Asmax.Max.Connection.MaxConnection
        """
        self._client = asmax_client
        self._connection = connection
        self._message_handlers: List[Callable] = []
        self._sticker_handlers: List[Callable] = []
        
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
        def delete_message_callback(payload):
            """Callback для ответа на удаление сообщения (cmd=1, opcode=66)"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на удаление сообщения (seq={seq})")
        
        def edit_message_callback(payload):
            """Callback для ответа на редактирование сообщения (cmd=1, opcode=67)"""
            seq = payload.get("seq", 0)
            if seq in self._pending_requests:
                future = self._pending_requests.pop(seq)
                if not future.done():
                    future.set_result(payload)
                    logger.debug(f"Получен ответ на редактирование сообщения (seq={seq})")
        
        # Регистрируем пакеты ответов
        from Asmax.Utils.MaxUtils import MaxUtils
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 66),
            DeleteMessageAnswerPacket,
            {"callback": delete_message_callback}
        )
        
        self._connection.register_packet(
            PacketHeader(MaxUtils.global_ver, 1, -1, 67),
            EditMessageAnswerPacket,
            {"callback": edit_message_callback}
        )
    
    async def send_message(self, chat_id: int, text: str, notify: bool = True) -> Message:
        """
        Отправить текстовое сообщение
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            notify: Уведомлять ли получателя
        
        Returns:
            Message: Отправленное сообщение
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        packet = SendMessagePacket(self._client.ws)
        packet.send_packet(chat_id, text, notify)
        
        # TODO: Получить ID отправленного сообщения из ответа
        return Message(
            id="",
            chat_id=chat_id,
            sender_id=0,
            text=text,
            date=datetime.now()
        )
    
    async def reply_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: str,
        notify: bool = True
    ) -> Message:
        """
        Ответить на сообщение
        
        Args:
            chat_id: ID чата
            text: Текст ответа
            reply_to_message_id: ID сообщения, на которое отвечаем
            notify: Уведомлять ли получателя
        
        Returns:
            Message: Отправленное сообщение
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        packet = SendReplyMessagePacket(self._client.ws)
        packet.send_packet(chat_id, text, reply_to_message_id, notify)
        
        return Message(
            id="",
            chat_id=chat_id,
            sender_id=0,
            text=text,
            date=datetime.now(),
            is_reply=True,
            reply_to_id=reply_to_message_id
        )
    
    async def send_sticker(
        self,
        chat_id: int,
        sticker_id: int,
        notify: bool = True
    ) -> Message:
        """
        Отправить стикер
        
        Args:
            chat_id: ID чата
            sticker_id: ID стикера
            notify: Уведомлять ли получателя
        
        Returns:
            Message: Отправленное сообщение
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        packet = SendStickerPacket(self._client.ws)
        packet.send_packet(chat_id, sticker_id, notify)
        
        return Message(
            id="",
            chat_id=chat_id,
            sender_id=0,
            text="",
            date=datetime.now(),
            type="sticker"
        )
    
    def on_message(self, handler: Callable[[Message], Awaitable[None]]):
        """
        Зарегистрировать обработчик входящих сообщений
        
        Args:
            handler: Функция(message: Message) -> None
        """
        self._message_handlers.append(handler)
        
        async def wrapper(asmax_msg: AsmaxMessage):
            try:
                # Конвертируем Asmax.Message в наш Message
                msg = Message.from_asmax(asmax_msg)
                await handler(msg)
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
        
        self._client.handlers.add_message_handler(wrapper)
    
    def on_sticker(self, handler: Callable[[Message, dict], Awaitable[None]]):
        """
        Зарегистрировать обработчик стикеров
        
        Args:
            handler: Функция(message: Message, attach: dict) -> None
        """
        self._sticker_handlers.append(handler)
        
        async def wrapper(asmax_msg: AsmaxMessage, attach: dict):
            try:
                msg = Message.from_asmax(asmax_msg)
                await handler(msg, attach)
            except Exception as e:
                logger.error(f"Ошибка обработки стикера: {e}", exc_info=True)
        
        self._client.handlers.add_sticker_handler(wrapper)
    
    async def delete_message(
        self,
        chat_id: int,
        message_ids: List[str],
        for_me: bool = False,
        wait_response: bool = True
    ) -> Dict:
        """
        Удалить сообщение(я)
        
        Args:
            chat_id: ID чата
            message_ids: Список ID сообщений для удаления
            for_me: True - удалить только у себя, False - удалить у всех
            wait_response: True - ждать ответа от сервера, False - только отправить запрос
        
        Returns:
            Dict с информацией об удалённых сообщениях (если wait_response=True)
            Или пустой dict если wait_response=False
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        if not message_ids:
            raise ValueError("Список message_ids не может быть пустым")
        
        # Отправляем запрос
        packet = DeleteMessagePacket(self._client.ws)
        seq = self._get_next_seq()
        packet.send_packet(chat_id, message_ids, for_me, seq)
        
        logger.info(f"Отправлен запрос на удаление сообщений в чате {chat_id} (seq={seq}, wait_response={wait_response})")
        
        if not wait_response:
            # Не ждем ответа, просто возвращаем информацию о запросе
            return {"chatId": chat_id, "messageIds": message_ids}
        
        # Ждём ответ (старая логика)
        future = asyncio.Future()
        self._pending_requests[seq] = future
        
        try:
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                logger.info(f"Сообщения успешно удалены из чата {chat_id}")
                return response
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при удалении сообщений")
                raise ConnectionError("Таймаут при удалении сообщений")
        
        finally:
            self._pending_requests.pop(seq, None)
    
    async def edit_message(
        self,
        chat_id: int,
        message_id: str,
        new_text: str
    ) -> Message:
        """
        Отредактировать сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения для редактирования
            new_text: Новый текст сообщения
        
        Returns:
            Message: Отредактированное сообщение
        
        Raises:
            ConnectionError: Клиент не подключён
        """
        if not hasattr(self._client, 'ws') or not self._client.ws:
            raise ConnectionError("Клиент не подключён")
        
        # Создаём Future для ожидания ответа
        future = asyncio.Future()
        seq = self._get_next_seq()
        self._pending_requests[seq] = future
        
        try:
            # Отправляем запрос
            packet = EditMessagePacket(self._client.ws)
            packet.send_packet(chat_id, message_id, new_text, seq)
            
            logger.info(f"Отправлен запрос на редактирование сообщения {message_id} в чате {chat_id} (seq={seq})")
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(future, timeout=10.0)
                
                # Парсим ответ
                message_data = response.get("message", {})
                if message_data:
                    # Конвертируем ответ в Message
                    timestamp = message_data.get("time", 0)
                    if timestamp:
                        msg_date = datetime.fromtimestamp(timestamp / 1000)
                    else:
                        msg_date = datetime.now()
                    
                    sender_id = message_data.get("sender", 0)
                    if isinstance(sender_id, dict):
                        sender_id = sender_id.get('id', 0)
                    
                    return Message(
                        id=str(message_data.get("id", message_id)),
                        chat_id=chat_id,
                        sender_id=sender_id,
                        text=message_data.get("text", new_text),
                        date=msg_date
                    )
                else:
                    # Если нет данных, возвращаем базовое сообщение
                    return Message(
                        id=message_id,
                        chat_id=chat_id,
                        sender_id=0,
                        text=new_text,
                        date=datetime.now()
                    )
            except asyncio.TimeoutError:
                logger.warning("Таймаут ожидания ответа при редактировании сообщения")
                raise ConnectionError("Таймаут при редактировании сообщения")
        
        finally:
            self._pending_requests.pop(seq, None)

