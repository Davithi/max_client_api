# Полная инструкция по проекту max_userapi

## 📋 Обзор проекта

**max_userapi** — высокоуровневая Python-библиотека для работы с Max Messenger UserAPI поверх библиотеки Asmax.

### Основная концепция

- **Чистая Python-библиотека** (без HTTP/REST серверов, без FastAPI/Flask)
- **Высокоуровневый интерфейс** поверх низкоуровневого Asmax
- **Async/await** паттерн во всех методах
- **Простой и понятный API** для пользователя

## 📁 Структура проекта

```
max_userapi/
├── max_userapi/              # Основная библиотека
│   ├── __init__.py          # Экспорты всех публичных классов
│   ├── client.py            # Главный класс UserAPI
│   ├── auth.py              # Менеджер авторизации (SMS, токен)
│   ├── messages.py          # Менеджер сообщений (отправка/получение)
│   ├── dialogs.py           # Менеджер диалогов (список чатов)
│   ├── groups.py            # Менеджер групп (✅ РЕАЛИЗОВАН)
│   ├── groups_packets.py    # Пакеты для работы с группами
│   ├── models.py            # Модели данных (User, Chat, Message, etc.)
│   └── exceptions.py        # Кастомные исключения
├── examples/                 # Примеры использования
│   ├── login_and_save_session.py
│   ├── send_message.py
│   ├── listen_updates.py
│   └── create_group_and_rename.py
├── setup.py                  # Установка пакета
├── pyproject.toml           # Современная конфигурация
├── requirements.txt         # Зависимости (Asmax>=0.1.1)
├── README.md                # Основная документация
├── NOTES.md                 # Примечания по реализации групп
└── .gitignore              # Git ignore файл
```

## 🔌 Зависимости

- **Asmax >= 0.1.1** — низкоуровневая библиотека для работы с Max Messenger
- **Python 3.10+**
- **websocket-client** (через Asmax)
- **UserAgenter** (через Asmax)

## ✅ Что реализовано

### 1. Авторизация (`auth.py`)
- ✅ `login_via_sms()` — авторизация по SMS-коду
- ✅ Автоматическое сохранение токена в файл `{session_name}.max`
- ✅ Авторизация по сохранённому токену
- ✅ Callback для ввода SMS-кода

### 2. Сообщения (`messages.py`)
- ✅ `send_message()` — отправка текстовых сообщений
- ✅ `reply_message()` — ответ на сообщение
- ✅ `send_sticker()` — отправка стикеров
- ✅ Обработка входящих сообщений через `on_message()`
- ✅ Обработка стикеров через `on_sticker()`

### 3. Диалоги (`dialogs.py`)
- ⚠️ Структура готова, но методы требуют исследования протокола
- `get_dialogs()` — получение списка чатов
- `get_chat()` — информация о чате
- `get_chat_history()` — история сообщений
- `search_chats()` — поиск чатов

### 4. Группы (`groups.py`) — ✅ ПОЛНОСТЬЮ РЕАЛИЗОВАНО
- ✅ `create_group()` — создание группы
- ✅ `set_group_title()` — изменение названия
- ✅ `add_group_members()` — добавление участников
- ✅ `remove_group_members()` — удаление участников
- ✅ `get_group_info()` — получение информации о группе

**Важно:** Используются предполагаемые opcode (65-69). Могут потребовать корректировки после исследования протокола.

### 5. Главный клиент (`client.py`)
- ✅ `UserAPI` класс с простым интерфейсом
- ✅ `connect()` — подключение к серверу
- ✅ `login_via_sms()` / `login_by_token()` — авторизация
- ✅ `send_message()` — отправка сообщений
- ✅ `listen_updates()` — подписка на обновления
- ✅ Все методы для работы с группами
- ✅ `is_connected()` / `disconnect()` — управление соединением

## 🔧 Как работает библиотека

### Архитектура

```
UserAPI (высокоуровневый интерфейс)
    ↓
Managers (auth, messages, dialogs, groups)
    ↓
Asmax (низкоуровневые пакеты и WebSocket)
    ↓
Max Messenger WebSocket API
```

### Паттерн работы с пакетами

1. **Создание пакета** — наследование от `Packet` или `AnswerPacket`
2. **Отправка запроса** — вызов `packet.send_packet()`
3. **Регистрация обработчика** — через `connection.register_packet()`
4. **Обработка ответа** — callback в `AnswerPacket.process()`

Пример (из `messages.py`):
```python
packet = SendMessagePacket(self._client.ws)
packet.send_packet(chat_id, text, notify)
```

### Асинхронное ожидание ответов (для групп)

Для операций, требующих ответа от сервера:
```python
# Создаём Future
future = asyncio.Future()
seq = self._get_next_seq()
self._pending_requests[seq] = future

# Отправляем пакет
packet = CreateGroupPacket(self._client.ws)
packet.header.seq = seq
packet.send_packet(...)

# Ждём ответ
response = await asyncio.wait_for(future, timeout=10.0)
```

## ⚠️ Важные замечания

### Opcode для групп

Используются **предполагаемые** opcode:
- 65 — создание группы
- 66 — обновление настроек
- 67 — добавление участников
- 68 — удаление участников
- 69 — получение информации о чате

**Если методы групп не работают:**
1. Перехватите WebSocket трафик при работе с группами через приложение Max Messenger
2. Найдите реальные opcode в JSON пакетах
3. Обновите opcode в `groups_packets.py`

### Структура пакетов

Все пакеты должны:
- Наследоваться от `Packet` (запросы) или `AnswerPacket` (ответы)
- Использовать `PacketHeader(ver, cmd, seq, opcode)`
- `cmd=0` для запросов, `cmd=1` для ответов
- `seq` используется для сопоставления запросов и ответов

## 📝 Примеры использования

### Базовое использование

```python
from max_userapi import UserAPI
import asyncio

async def main():
    api = UserAPI(session_name="my_session")
    await api.connect()
    await api.login_by_token()  # или login_via_sms()
    
    # Отправка сообщения
    await api.send_message(chat_id=123, text="Привет!")
    
    # Создание группы
    group = await api.create_group("Моя группа", [123, 456])
    await api.set_group_title(group.id, "Новое название")

asyncio.run(main())
```

### Обработка входящих сообщений

```python
async def handle_update(update):
    if update.type == "message":
        print(f"Новое сообщение: {update.message.text}")

await api.listen_updates(handle_update)
```

## 🐛 Отладка

### Если методы групп не работают

1. **Проверьте логи** — все предупреждения о таймаутах логируются
2. **Проверьте opcode** — используйте перехват трафика для определения правильных opcode
3. **Проверьте структуру payload** — она может отличаться от предполагаемой
4. **Проверьте sequence numbers** — они должны совпадать в запросах и ответах

### Логирование

Включите логирование для отладки:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Интеграция с Asmax

Библиотека использует Asmax для:
- WebSocket соединения (`MaxClient`, `MaxConnection`)
- Отправки пакетов (`Packet.send()`)
- Получения пакетов (`AnswerPacket.process()`)
- Регистрации обработчиков (`connection.register_packet()`)

Не изменяем исходный код Asmax — используем его как зависимость.

## 📦 Установка и использование

### Установка

```bash
cd max_userapi
pip install -e .
```

### Запуск примеров

```bash
python examples/login_and_save_session.py
python examples/send_message.py
python examples/create_group_and_rename.py
```

## 🚀 Что можно добавить в будущем

1. **Реализация диалогов** — после исследования протокола
2. **Получение истории сообщений** — требуется соответствующий пакет
3. **Работа с файлами/медиа** — отправка фото, видео и т.д.
4. **Улучшенная обработка ошибок** — более детальные исключения
5. **Тесты** — unit и integration тесты
6. **Документация API** — более подробная документация по всем методам

## 📚 Ключевые файлы для понимания

1. **`client.py`** — главный интерфейс библиотеки
2. **`groups.py`** — пример полной реализации менеджера
3. **`groups_packets.py`** — пример создания пакетов
4. **`messages.py`** — пример работы с существующими пакетами Asmax
5. **`models.py`** — структуры данных

## 🔗 Репозиторий

- GitHub: https://github.com/Davithi/max_user_api_python.git
- Основная зависимость: Asmax (https://github.com/WallD3v/Asmax)

## 💡 Советы для работы

1. **Всегда используйте async/await** — библиотека полностью асинхронная
2. **Проверяйте подключение** — используйте `is_connected()` перед операциями
3. **Обрабатывайте исключения** — `ConnectionError`, `AuthError`, etc.
4. **Сохраняйте сессии** — токен автоматически сохраняется в файл
5. **Изучайте примеры** — в `examples/` есть готовые скрипты

## ❓ Частые вопросы

**Q: Почему методы групп возвращают ошибку?**  
A: Скорее всего, opcode неверны. Используйте перехват трафика для определения правильных значений.

**Q: Как получить список всех чатов?**  
A: Метод `get_dialogs()` требует реализации пакета после исследования протокола.

**Q: Можно ли использовать без Asmax?**  
A: Нет, библиотека полностью зависит от Asmax для низкоуровневой работы с протоколом.

**Q: Как добавить новый метод?**  
A: Создайте пакет (как в `groups_packets.py`), добавьте метод в соответствующий менеджер, добавьте прокси-метод в `UserAPI`.

---

**Дата создания инструкции:** 2024  
**Версия библиотеки:** 0.1.0  
**Последнее обновление:** После реализации групп

