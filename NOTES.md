# Примечания по реализации работы с группами

## Реализованные методы

Все методы работы с группами реализованы в `max_userapi/groups.py` и доступны через `UserAPI`:

- ✅ `create_group(title, member_ids)` - создание группы
- ✅ `set_group_title(chat_id, new_title)` - изменение названия
- ✅ `add_group_members(chat_id, member_ids)` - добавление участников
- ✅ `remove_group_members(chat_id, member_ids)` - удаление участников  
- ✅ `get_group_info(chat_id)` - получение информации о группе

## Важное замечание об Opcode

Используемые opcode (65-69) являются **предполагаемыми** и основаны на логике протокола:
- Opcode для запросов обычно cmd=0
- Opcode для ответов обычно cmd=1
- Номера opcode выбраны последовательно после существующих (64 для сообщений)

**Если методы не работают, скорее всего нужно скорректировать opcode.**

### Как определить правильные opcode:

1. Запустите приложение Max Messenger
2. Используйте инструменты разработчика или перехватчик WebSocket трафика
3. Выполните действие (создание группы, изменение названия и т.д.)
4. Найдите соответствующие пакеты в трафике
5. Определите opcode из поля `opcode` в JSON пакетах
6. Обновите opcode в файле `max_userapi/groups_packets.py`

## Структура пакетов

Все пакеты для групп находятся в `max_userapi/groups_packets.py`:
- `CreateGroupPacket` / `CreateGroupAnswerPacket` (opcode 65)
- `UpdateGroupSettingsPacket` / `UpdateGroupSettingsAnswerPacket` (opcode 66)
- `AddGroupMembersPacket` / `AddGroupMembersAnswerPacket` (opcode 67)
- `RemoveGroupMembersPacket` / `RemoveGroupMembersAnswerPacket` (opcode 77 - CHAT_MEMBERS_UPDATE)
- `GetChatInfoPacket` / `GetChatInfoAnswerPacket` (opcode 69)

## Механизм работы

1. При создании запроса создаётся `Future` для ожидания ответа
2. Пакет отправляется с уникальным `seq` (sequence number)
3. Ответ регистрируется через `register_packet` в `MaxConnection`
4. Когда приходит ответ с соответствующим opcode, вызывается callback
5. Callback завершает `Future` с результатом
6. Метод возвращает результат или выбрасывает исключение при таймауте

## Пример использования

```python
from max_userapi import UserAPI
import asyncio

async def main():
    api = UserAPI("my_session")
    await api.connect()
    await api.login_by_token()
    
    # Создание группы
    group = await api.create_group("Test Group", member_ids=[12345, 67890])
    print(f"Создана группа: {group.title} (ID: {group.id})")
    
    # Изменение названия
    await api.set_group_title(group.id, "New Group Name")
    
    # Получение информации
    info = await api.get_group_info(group.id)
    print(f"Участников: {info.member_count}")

asyncio.run(main())
```

## Отладка

Если методы не работают:

1. Проверьте логи - все предупреждения о таймаутах логируются
2. Убедитесь, что opcode корректны (см. выше)
3. Проверьте структуру payload - она может отличаться от предполагаемой
4. Используйте инструменты перехвата WebSocket для анализа реальных пакетов

