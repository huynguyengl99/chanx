from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from chat.models import ChatMember, GroupChat


class ReadOnlyMemberOrOwner(permissions.BasePermission):
    message = "Only group owner can modify state, or a member to fetch"

    def has_object_permission(
        self, request: Request, view: APIView, obj: GroupChat
    ) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return ChatMember.objects.filter(
                user=request.user.pk, group_chat=obj
            ).exists()
        else:
            return ChatMember.objects.filter(
                user=request.user.pk,
                group_chat=obj,
                chat_role=ChatMember.ChatMemberRole.OWNER,
            ).exists()


class IsGroupChatMember(permissions.BasePermission):
    message = "Only group members are allowed."

    def has_object_permission(
        self, request: Request, view: APIView, obj: GroupChat
    ) -> bool:
        return ChatMember.objects.filter(
            user=request.user.pk,
            group_chat=obj,
        ).exists()


class GroupChatManagerOrMemberReadonly(permissions.BasePermission):
    message = "Only group managers can access this nested api."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return ChatMember.objects.filter(
                user=request.user.pk,
                group_chat_id=view.kwargs.get("group_chat_pk"),
            ).exists()
        else:
            return ChatMember.objects.filter(
                user=request.user.pk,
                group_chat_id=view.kwargs.get("group_chat_pk"),
                chat_role__lte=ChatMember.ChatMemberRole.ADMIN,
            ).exists()


class IsGroupChatMemberNested(permissions.BasePermission):
    message = "Only group members are allowed for these nested route apis."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return ChatMember.objects.filter(
            user=request.user.pk,
            group_chat=view.kwargs.get("group_chat_pk"),
        ).exists()
