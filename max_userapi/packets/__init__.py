"""Пакеты протокола для работы с Max Messenger"""
from .groups import (
    CreateGroupPacket,
    CreateGroupAnswerPacket,
    UpdateGroupSettingsPacket,
    UpdateGroupSettingsAnswerPacket,
    AddGroupMembersPacket,
    AddGroupMembersAnswerPacket,
    RemoveGroupMembersPacket,
    RemoveGroupMembersAnswerPacket,
    GetChatInfoPacket,
    GetChatInfoAnswerPacket,
    GetAuthStatePacket,
    UpdateGroupOptionsPacket,
    UpdateGroupOptionsAnswerPacket,
    GetGroupPreviewByLinkPacket,
    GetGroupPreviewByLinkAnswerPacket,
)
from .contacts import (
    ResolvePhonePacket,
    ResolvePhoneAnswerPacket,
)
from .messages import (
    DeleteMessagePacket,
    DeleteMessageAnswerPacket,
    EditMessagePacket,
    EditMessageAnswerPacket,
)
from .dialogs import (
    GetChatHistoryPacket,
    GetChatHistoryAnswerPacket,
    GetChatsListPacket,
    GetChatsListAnswerPacket,
)
from .notifications import (
    TypingNotificationPacket,
    ChatUpdateNotificationPacket,
)

__all__ = [
    'CreateGroupPacket',
    'CreateGroupAnswerPacket',
    'UpdateGroupSettingsPacket',
    'UpdateGroupSettingsAnswerPacket',
    'AddGroupMembersPacket',
    'AddGroupMembersAnswerPacket',
    'RemoveGroupMembersPacket',
    'RemoveGroupMembersAnswerPacket',
    'GetChatInfoPacket',
    'GetChatInfoAnswerPacket',
    'GetAuthStatePacket',
    'UpdateGroupOptionsPacket',
    'UpdateGroupOptionsAnswerPacket',
    'GetGroupPreviewByLinkPacket',
    'GetGroupPreviewByLinkAnswerPacket',
    'ResolvePhonePacket',
    'ResolvePhoneAnswerPacket',
    'DeleteMessagePacket',
    'DeleteMessageAnswerPacket',
    'EditMessagePacket',
    'EditMessageAnswerPacket',
    'GetChatHistoryPacket',
    'GetChatHistoryAnswerPacket',
    'GetChatsListPacket',
    'GetChatsListAnswerPacket',
    'TypingNotificationPacket',
    'ChatUpdateNotificationPacket',
]

