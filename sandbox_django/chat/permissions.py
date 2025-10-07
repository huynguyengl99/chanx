from typing import cast

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from chat.models import ChatMember, GroupChat
from utils.request import AuthenticatedRequest


class ReadOnlyMemberOrOwner(permissions.BasePermission):
    message = "Only group owner can modify state, or a member to fetch"

    def has_object_permission(
        self, request: Request, view: APIView, obj: GroupChat
    ) -> bool:
        request = cast(AuthenticatedRequest, request)

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
    """
    Permission to only allow members of a group chat to access it.

    This permission expects the view to have a 'pk' URL parameter
    representing the group chat ID.
    """

    message = "You are not a member of this group chat."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        request_auth = cast(AuthenticatedRequest, request)
        group_chat_pk = view.kwargs.get("pk")

        if not group_chat_pk:
            return False

        return ChatMember.objects.filter(
            user=request_auth.user, group_chat_id=group_chat_pk
        ).exists()


class IsGroupChatMemberNested(permissions.BasePermission):
    message = "Only group members are allowed for these nested route apis."

    def has_permission(self, request: Request, view: APIView) -> bool:
        request = cast(AuthenticatedRequest, request)

        return ChatMember.objects.filter(
            user=request.user.pk,
            group_chat=view.kwargs.get("group_chat_pk"),
        ).exists()
