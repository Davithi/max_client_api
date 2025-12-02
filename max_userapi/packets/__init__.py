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
)
from .contacts import (
    ResolvePhonePacket,
    ResolvePhoneAnswerPacket,
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
    'ResolvePhonePacket',
    'ResolvePhoneAnswerPacket',
]

