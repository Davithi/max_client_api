# max_userapi

Высокоуровневая Python-библиотека для работы с Max Messenger UserAPI поверх [Asmax](https://github.com/WallD3v/Asmax).

## Описание

`max_userapi` предоставляет простой и понятный интерфейс для работы с Max Messenger через WebSocket API. Библиотека скрывает низкоуровневые детали протокола и предоставляет удобные методы для:

- Авторизации по SMS-коду
- Отправки и получения сообщений
- Работы с диалогами и группами
- Создания и управления группами (после исследования протокола)

## Требования

- Python 3.10+
- Asmax >= 0.1.1

## Установка

```bash
pip install max-userapi
```

Или из исходников:

```bash
git clone https://github.com/yourusername/max_userapi.git
cd max_userapi
pip install -e .
```

## Быстрый старт

### Подключение и авторизация

```python
import asyncio
from max_userapi import UserAPI

async def main():
    # Создаём клиент
    api = UserAPI(session_name="my_session")
    
    # Подключаемся
    await api.connect()
    
    # Авторизуемся по номеру телефона
    await api.login_via_sms(
        phone="+79991234567",
        code_callback=lambda token: input("Введите SMS-код: ")
    )
    
    print("Авторизация успешна!")

asyncio.run(main())
```

### Отправка сообщения

```python
import asyncio
from max_userapi import UserAPI

async def main():
    api = UserAPI(session_name="my_session")
    await api.connect()
    
    # Отправляем сообщение
    message = await api.send_message(
        chat_id=123456789,
        text="Привет из max_userapi!"
    )
    
    print(f"Сообщение отправлено: {message.text}")

asyncio.run(main())
```

### Получение входящих сообщений

```python
import asyncio
from max_userapi import UserAPI, Update

async def main():
    api = UserAPI(session_name="my_session")
    await api.connect()
    
    # Обработчик обновлений
    async def handle_update(update: Update):
        if update.type == "message" and update.message:
            msg = update.message
            print(f"Новое сообщение в {msg.chat_id}: {msg.text}")
    
    # Подписываемся на обновления
    await api.listen_updates(handle_update)
    
    # Бесконечный цикл
    while api.is_connected():
        await asyncio.sleep(1)

asyncio.run(main())
```

### Создание группы

```python
import asyncio
from max_userapi import UserAPI

async def main():
    api = UserAPI(session_name="my_session")
    await api.connect()
    
    # Создаём группу
    group = await api.create_group(
        title="Моя группа",
        member_ids=[123456, 789012, 345678]
    )
    
    print(f"Группа создана: {group.title} (ID: {group.id})")
    
    # Изменяем название
    await api.set_group_title(
        chat_id=group.id,
        new_title="Новое название"
    )

asyncio.run(main())
```

**Примечание**: Методы работы с группами (`create_group`, `set_group_title` и т.д.) требуют исследования протокола Max Messenger. Сейчас они возвращают `NotImplementedError`. Для реализации необходимо:

1. Перехватить WebSocket трафик при создании/изменении группы через приложение Max Messenger
2. Определить opcode и структуру пакетов
3. Реализовать соответствующие пакеты в Asmax или напрямую в max_userapi

## Примеры

В папке `examples/` находятся готовые примеры использования:

- `login_and_save_session.py` - авторизация и сохранение сессии
- `send_message.py` - отправка сообщения
- `listen_updates.py` - получение входящих сообщений
- `create_group_and_rename.py` - создание группы (требует реализации)

Запуск примеров:

```bash
python examples/login_and_save_session.py
```

## API Документация

### UserAPI

Главный класс библиотеки.

#### Методы

- `connect()` - Подключение к серверу
- `login_via_sms(phone, code_callback)` - Авторизация по SMS
- `send_message(chat_id, text)` - Отправка сообщения
- `get_dialogs(limit)` - Получение списка диалогов (требует реализации)
- `listen_updates(handler)` - Подписка на обновления
- `create_group(title, member_ids)` - Создание группы (требует реализации)
- `set_group_title(chat_id, new_title)` - Изменение названия группы (требует реализации)
- `add_group_members(chat_id, member_ids)` - Добавление участников (требует реализации)
- `remove_group_members(chat_id, member_ids)` - Удаление участников (требует реализации)
- `get_group_info(chat_id)` - Получение информации о группе (требует реализации)
- `is_connected()` - Проверка подключения
- `disconnect()` - Отключение

### Модели данных

- `User` - Пользователь
- `Dialog` - Диалог/Чат
- `Chat` - Чат (группа или личный)
- `Message` - Сообщение
- `GroupInfo` - Информация о группе
- `Update` - Входящее обновление

## Архитектура

Библиотека состоит из модулей:

- `client.py` - Главный класс UserAPI
- `auth.py` - Менеджер авторизации
- `messages.py` - Менеджер работы с сообщениями
- `dialogs.py` - Менеджер работы с диалогами
- `groups.py` - Менеджер работы с группами
- `models.py` - Модели данных (dataclasses)
- `exceptions.py` - Исключения

## Лицензия

MIT

## Связь с Asmax

Эта библиотека использует [Asmax](https://github.com/WallD3v/Asmax) для низкоуровневой работы с протоколом Max Messenger. Asmax отвечает за:

- WebSocket соединение
- Отправку и получение пакетов
- Базовую авторизацию
- Обработку протокольных деталей

`max_userapi` предоставляет высокоуровневый интерфейс поверх Asmax, скрывая детали протокола и предоставляя удобные методы для работы.

## Вклад в проект

Приветствуются pull request'ы! Особенно полезны:

- Реализация методов работы с группами (требуется исследование протокола)
- Улучшение обработки ошибок
- Добавление новых функций
- Исправление багов

## Поддержка

Если у вас есть вопросы или проблемы, создайте issue на GitHub.

