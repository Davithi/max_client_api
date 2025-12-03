"""Модуль авторизации"""
import asyncio
import logging
import threading
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
        self._auth_code: Optional[str] = None  # Сохраняем код, полученный из callback
        # Используем threading.Event для синхронизации между потоками
        self._auth_code_event = threading.Event()
        self._user: Optional[User] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Перехватываем callback авторизации
        self._intercept_auth_flow()
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Устанавливает event loop для использования из других потоков"""
        self._loop = loop
    
    def _intercept_auth_flow(self):
        """Перехватывает поток авторизации для обработки SMS-кода"""
        # Ищем зарегистрированный AuthAnswerPacket
        for r_packet in self._client.conn.registered_classes:
            if hasattr(r_packet, 'clazz') and r_packet.clazz == AuthAnswerPacket:
                original_callback = r_packet.custom_data.get('return_method')
                
                def auth_callback_wrapper(code: str, token: str):
                    # Сохраняем код и токен
                    self._auth_token = token
                    self._auth_code = code
                    # Устанавливаем threading.Event из любого потока
                    self._auth_code_event.set()
                    # Вызываем оригинальный callback для отправки кода
                    if original_callback:
                        original_callback(code, token)
                
                r_packet.custom_data['return_method'] = auth_callback_wrapper
                break
    
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
            self._auth_code_event.clear()  # Очищаем event перед использованием
            self._auth_token = None
            self._auth_code = None  # Очищаем сохраненный код
            
            logger.info(f"Запрос SMS-кода для {phone}...")
            await self._client.auth(phone)
            
            # Ждём получения токена (используем threading.Event в async контексте)
            try:
                # Ждём threading.Event в async контексте
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, self._auth_code_event.wait),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                raise AuthError("Таймаут ожидания ответа на запрос кода")
            
            if not self._auth_token:
                raise AuthError("Не получен токен для отправки кода")
            
            # Получаем код - либо из сохраненного (если уже был введен через оригинальный callback),
            # либо через наш callback
            if self._auth_code:
                # Код уже был получен и отправлен через оригинальный callback
                code = self._auth_code
                logger.info("Используется код, введенный через оригинальный callback")
                # Код уже отправлен оригинальным callback, просто ждем
            else:
                # Получаем код через наш callback
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

