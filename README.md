# max_userapi

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-alpha-orange)

**Асинхронная Python-библиотека для работы с мессенджером [Max](https://max.ru) от имени пользователя (UserAPI).**

Авторизация по SMS, отправка и получение сообщений, диалоги, контакты и полное управление группами — через простой `async/await` интерфейс поверх [Asmax](https://github.com/WallD3v/Asmax).

> ⚠️ Неофициальная библиотека. Не связана с командой Max. Используйте на свой страх и риск и соблюдайте правила сервиса.

```python
api = UserAPI(session_name="my_session")
await api.connect()
await api.login_via_sms(phone="+79991234567")
await api.send_message(chat_id=123456789, text="Привет из Python! 👋")
```

## Возможности

- 🔐 **Авторизация** — по SMS-коду и по сохранённому токену сессии
- 💬 **Сообщения** — отправка, редактирование, удаление, приём входящих и стикеров в реальном времени
- 📋 **Диалоги** — список чатов
- 👥 **Контакты** — список контактов, поиск по ID и номеру телефона
- 🏘 **Группы** — создание, название и описание, добавление/удаление участников, инвайт-ссылки, вступление и выход, настройки прав
- ⚡ **Асинхронность** — все сетевые методы на `asyncio`

## Установка

Требуется Python 3.10+.

```bash
git clone https://github.com/Davithi/max_client_api.git max_userapi
pip install -r max_userapi/requirements.txt
```

Папка должна называться `max_userapi` — импортируйте библиотеку из родительской директории:

```python
from max_userapi import UserAPI
```

## Быстрый старт

### Первый вход по SMS

```python
import asyncio
from max_userapi import UserAPI

async def main():
    api = UserAPI(session_name="my_session")  # токен сохранится в my_session.max
    await api.connect()
    await api.login_via_sms(
        phone="+79991234567",
        code_callback=lambda token: input("Введите SMS-код: "),
    )
    print("Вошли как", api.get_current_user())

asyncio.run(main())
```

### Повторный вход по сохранённой сессии

```python
api = UserAPI(session_name="my_session")
await api.connect()
await api.login_by_token()
```

### Отправка, редактирование и удаление сообщений

```python
msg = await api.send_message(chat_id=123456789, text="Привет!")
await api.edit_message(chat_id=123456789, message_id=msg.id, new_text="Привет, мир!")
await api.delete_message(chat_id=123456789, message_ids=[msg.id], for_me=False)
```

### Приём входящих сообщений

```python
from max_userapi import UserAPI, Update

async def handle_update(update: Update):
    if update.type == "message":
        print(f"[{update.message.chat_id}] {update.message.text}")
    elif update.type == "sticker":
        print("Стикер:", update.data["sticker"])

await api.listen_updates(handle_update)

while api.is_connected():
    await asyncio.sleep(1)
```

### Работа с группами

```python
group = await api.create_group(title="Моя группа", member_ids=[111, 222])

await api.set_group_title(chat_id=group.id, new_title="Новое название")
await api.set_group_description(chat_id=group.id, description="Описание группы")
await api.add_group_members(chat_id=group.id, member_ids=[333])

link = await api.get_group_invite_link(chat_id=group.id)
print("Ссылка-приглашение:", link)

info = await api.get_group_info(chat_id=group.id)
print(info.title, info.member_count)
```

## Справочник API

Все методы класса `UserAPI` (кроме `get_current_user` и `is_connected`) асинхронные.

| Категория | Методы |
|---|---|
| Подключение | `connect()`, `disconnect()`, `is_connected()` |
| Авторизация | `login_via_sms(phone, code_callback)`, `login_by_token()`, `get_profile()`, `get_current_user()` |
| Сообщения | `send_message(chat_id, text)`, `edit_message(chat_id, message_id, new_text)`, `delete_message(chat_id, message_ids, for_me)`, `listen_updates(handler)` |
| Диалоги | `get_dialogs(limit, offset)` |
| Контакты | `get_contacts(limit, offset)`, `get_contact_by_id(contact_id)`, `get_contact_by_phone(phone)`, `check_phone(phone)` |
| Группы | `create_group`, `get_group_info`, `set_group_title`, `set_group_description`, `add_group_members`, `remove_group_members`, `leave_group`, `get_admin_groups` |
| Инвайт-ссылки | `get_group_invite_link`, `revoke_group_invite_link`, `join_group_by_link`, `get_group_preview_by_link` |
| Права в группе | `update_group_options`, `set_only_owner_can_change_icon_title`, `set_only_admin_can_add_member`, `set_all_can_pin_message`, `set_members_can_see_private_link`, `set_only_admin_can_call` |

**Модели:** `User`, `Contact`, `Dialog`, `Chat`, `Message`, `GroupInfo`, `Update`

**Исключения:** `MaxUserAPIError` (базовое), `AuthError`, `ConnectionError`, `ChatNotFoundError`, `GroupNotFoundError`

## Структура проекта

```
client.py      — главный класс UserAPI
managers/      — логика: auth, messages, dialogs, groups, contacts
packets/       — пакеты протокола Max
models/        — dataclass-модели
exceptions.py  — исключения
```

## Участие в проекте

Pull request'ы и issue приветствуются! Особенно полезно:

- поддержка медиа (фото, файлы, голосовые)
- тесты и примеры
- исследование новых opcode протокола

Если библиотека пригодилась — поставьте ⭐, это помогает проекту.

## Лицензия

MIT
