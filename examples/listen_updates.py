"""Пример: подписка и вывод новых входящих сообщений в консоль"""
import asyncio
import logging
from max_userapi import UserAPI, Update

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    api = UserAPI(session_name="my_session")
    
    try:
        # Подключаемся
        print("Подключение...")
        await api.connect()
        print("✓ Подключено")
        
        # Проверяем сессию
        if not api.auth.has_token():
            print("Сессия не найдена. Требуется авторизация.")
            phone = input("Введите номер телефона (+7XXXXXXXXXX): ")
            await api.login_via_sms(phone=phone)
        else:
            print("✓ Используется сохранённая сессия")
            await api.login_by_token()
        
        # Обработчик обновлений
        async def handle_update(update: Update):
            if update.type == "message" and update.message:
                msg = update.message
                print(f"\n📨 Новое сообщение:")
                print(f"   Чат ID: {msg.chat_id}")
                print(f"   От: {msg.sender_id}")
                print(f"   Текст: {msg.text}")
                print(f"   Время: {msg.date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            elif update.type == "sticker":
                print(f"\n🎭 Получен стикер в чате {update.message.chat_id if update.message else 'unknown'}")
        
        # Подписываемся на обновления
        await api.listen_updates(handle_update)
        print("✓ Ожидание сообщений... (Ctrl+C для остановки)")
        
        # Бесконечный цикл
        while api.is_connected():
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("\n⏹ Остановка...")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await api.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

