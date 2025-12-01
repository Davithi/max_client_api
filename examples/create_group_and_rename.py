"""Пример: создание группы с несколькими участниками и смена названия"""
import asyncio
import logging
from max_userapi import UserAPI

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
        
        # Пример создания группы
        print("\nСоздание группы...")
        title = input("Введите название группы: ")
        member_ids_input = input("Введите ID участников через запятую: ")
        member_ids = [int(x.strip()) for x in member_ids_input.split(",")]
        
        try:
            # Создание группы
            print(f"Создание группы '{title}' с участниками: {member_ids}...")
            group = await api.create_group(title=title, member_ids=member_ids)
            print(f"✓ Группа создана: {group.title} (ID: {group.id})")
            
            # Получение информации о группе
            print(f"\nПолучение информации о группе {group.id}...")
            info = await api.get_group_info(chat_id=group.id)
            print(f"✓ Информация о группе:")
            print(f"   Название: {info.title}")
            print(f"   Участников: {info.member_count}")
            print(f"   ID участников: {info.member_ids}")
            
            # Изменение названия
            new_title = input(f"\nВведите новое название (текущее: {group.title}): ")
            if new_title.strip():
                print(f"Изменение названия группы на '{new_title}'...")
                await api.set_group_title(chat_id=group.id, new_title=new_title)
                print(f"✓ Название изменено на: {new_title}")
            
        except NotImplementedError as e:
            print(f"⚠ Метод ещё не реализован: {e}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            print("\nВозможные причины:")
            print("1. Opcode для операций с группами могут отличаться от предполагаемых")
            print("2. Структура payload может быть другой")
            print("3. Требуется исследование протокола Max Messenger")
    
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

