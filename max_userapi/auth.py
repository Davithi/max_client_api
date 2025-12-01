"""Модуль авторизации"""
import asyncio
import logging
from typing import Optional, Callable
from .exceptions import AuthError
from .models import User

# Импорт из Asmax
from Asmax.Max.Client import MaxClient
from Asmax.Packets.AuthPacket import AuthAnswerPacket

logger = logging.getLogger(__name__)


class AuthManager:
    """Менеджер авторизации"""
    
    def __init__(self, asmax_client: MaxClient):
        """
        Args:
            asmax_client: Экземпляр Asmax.Max.Client.MaxClient
        """
        self._client = asmax_client
        self._sms_code_callback: Optional[Callable[[str], str]] = None
        self._auth_token: Optional[str] = None
        self._auth_code_event = asyncio.Event()
        self._user: Optional[User] = None
        
        # Перехватываем callback авторизации
        self._intercept_auth_flow()
    
    def _intercept_auth_flow(self):
        """Перехватывает поток авторизации для обработки SMS-кода"""
        # Ищем зарегистрированный AuthAnswerPacket
        for r_packet in self._client.conn.registered_classes:
            if hasattr(r_packet, 'clazz') and r_packet.clazz == AuthAnswerPacket:
                original_callback = r_packet.custom_data.get('return_method')
                
                def auth_callback_wrapper(code: str, token: str):
                    self._auth_token = token
                    asyncio.create_task(self._notify_auth_token_received())
                    if original_callback:
                        original_callback(code, token)
                
                r_packet.custom_data['return_method'] = auth_callback_wrapper
                break
    
    async def _notify_auth_token_received(self):
        """Уведомляет о получении токена для авторизации"""
        self._auth_code_event.set()
    
    async def login_via_sms(
        self,
        phone: str,
        code_callback: Optional[Callable[[str], str]] = None
    ) -> User:
        """
        Авторизация по SMS-коду
        
        Args:
            phone: Номер телефона в формате +7XXXXXXXXXX
            code_callback: Функция для получения SMS-кода.
                          Вызывается как callback(token: str) -> str
                          Если None - используется стандартный input()
        
        Returns:
            User: Авторизованный пользователь
        
        Raises:
            AuthError: Ошибка авторизации
        """
        try:
            self._sms_code_callback = code_callback or (lambda token: input("Введите SMS-код: "))
            self._auth_code_event.clear()
            self._auth_token = None
            
            logger.info(f"Запрос SMS-кода для {phone}...")
            await self._client.auth(phone)
            
            # Ждём получения токена
            try:
                await asyncio.wait_for(self._auth_code_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                raise AuthError("Таймаут ожидания ответа на запрос кода")
            
            if not self._auth_token:
                raise AuthError("Не получен токен для отправки кода")
            
            # Получаем код через callback
            logger.info("Ожидание ввода SMS-кода...")
            code = self._sms_code_callback(self._auth_token)
            
            if not code:
                raise AuthError("SMS-код не введён")
            
            # Отправляем код
            self._client.send_code(code, self._auth_token)
            
            # Ждём обработки ответа
            await asyncio.sleep(2)
            
            # Авторизуемся по токену
            if self._client.token:
                await self._client.auth_by_token()
                logger.info("Авторизация успешна")
                
                # TODO: Получить информацию о пользователе из ответа авторизации
                self._user = User(id=0, phone=phone)
                return self._user
            else:
                raise AuthError("Токен не сохранён после отправки кода")
        
        except Exception as e:
            if not isinstance(e, AuthError):
                raise AuthError(f"Ошибка авторизации: {e}") from e
            raise
    
    def get_token(self) -> Optional[str]:
        """Получить текущий токен"""
        return self._client.token
    
    def has_token(self) -> bool:
        """Проверить, есть ли сохранённый токен"""
        return self._client.token is not None
    
    @property
    def user(self) -> Optional[User]:
        """Получить текущего пользователя"""
        return self._user

