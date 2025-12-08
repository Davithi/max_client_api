"""Пример: загрузка сессии и отправка сообщения"""
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
        # Подключаемся
        print("Подключение...")
        await api.connect()
        print("✓ Подключено")
        
        # Если есть сохранённая сессия, она будет автоматически использована
        # Если нет - нужна авторизация через login_via_sms()
        
        # Проверяем, есть ли токен
        if not api.auth.has_token():
            print("Сессия не найдена. Требуется авторизация.")
            phone = input("Введите номер телефона (+7XXXXXXXXXX): ")
            await api.login_via_sms(phone=phone)
        else:
            print("✓ Используется сохранённая сессия")
            # Авторизуемся по токену
            await api.login_by_token()
        
        # Получаем chat_id и текст сообщения
        chat_id = int(input("Введите chat_id для отправки сообщения: "))
        text = input("Введите текст сообщения: ")
        
        # Отправляем сообщение
        print(f"Отправка сообщения в чат {chat_id}...")
        message = await api.send_message(chat_id=chat_id, text=text)
        
        print(f"✓ Сообщение отправлено: {message.text}")
    
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

