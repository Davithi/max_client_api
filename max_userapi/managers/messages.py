"""Модуль работы с сообщениями"""
from datetime import datetime
from typing import List, Callable, Awaitable
import asyncio
import logging
from ..models import Message
from ..exceptions import ConnectionError

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

