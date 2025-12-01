"""Пример: логин по номеру телефона и SMS-коду, сохранение сессии"""
import asyncio
import logging
from max_userapi import UserAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    # Создаём клиент с именем сессии
    api = UserAPI(session_name="my_session")
    
    try:
        # Подключаемся к серверу
        print("Подключение к серверу...")
        await api.connect()
        print("✓ Подключено")
        
        # Авторизуемся по номеру телефона
        phone = input("Введите номер телефона (+7XXXXXXXXXX): ")
        
        # Функция для получения SMS-кода
        def get_code(token: str) -> str:
            return input("Введите SMS-код: ")
        
        print(f"Запрос SMS-кода для {phone}...")
        await api.login_via_sms(phone=phone, code_callback=get_code)
        
        print("✓ Авторизация успешна!")
        print(f"✓ Сессия сохранена в файл: {api.session_name}.max")
        print("Теперь вы можете использовать эту сессию для авторизации без SMS-кода")
    
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    finally:
        await api.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

