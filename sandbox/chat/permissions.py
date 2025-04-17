from rest_framework import permissions

from chat.models import ChatMember


class ReadOnlyMemberOrOwner(permissions.BasePermission):
    message = "Only group owner can modify state, or a member to fetch"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return ChatMember.objects.filter(user=request.user, group_chat=obj).exists()
        else:
            return ChatMember.objects.filter(
                user=request.user,
                group_chat=obj,
                chat_role=ChatMember.ChatMemberRole.OWNER,
            ).exists()


class IsGroupChatMember(permissions.BasePermission):
    message = "Only group members are allowed."

    def has_object_permission(self, request, view, obj):
        return ChatMember.objects.filter(
            user=request.user,
            group_chat=obj,
        ).exists()
