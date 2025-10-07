from django.contrib import admin

from .models import ChatMember, ChatMessage, GroupChat


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin[ChatMember]):
    list_display = (
        "id",
        "chat_role",
        "group_chat",
        "user",
    )
    list_filter = ("group_chat", "user")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin[ChatMessage]):
    list_display = (
        "id",
        "group_chat",
        "sender",
    )
    list_filter = (
        "group_chat",
        "sender",
    )


@admin.register(GroupChat)
class GroupChatAdmin(admin.ModelAdmin[GroupChat]):
    list_display = (
        "id",
        "title",
        "description",
    )
    raw_id_fields = ("users",)
