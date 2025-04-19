from django.contrib import admin

from .models import ChatMember, ChatMessage, GroupChat


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "chat_role",
        "group_chat",
        "user",
    )
    list_filter = ("created", "modified", "group_chat", "user")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "group_chat",
        "sender",
    )
    list_filter = (
        "created",
        "modified",
        "group_chat",
        "sender",
    )


@admin.register(GroupChat)
class GroupChatAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "modified",
        "title",
        "description",
    )
    list_filter = ("created", "modified")
    raw_id_fields = ("users",)
