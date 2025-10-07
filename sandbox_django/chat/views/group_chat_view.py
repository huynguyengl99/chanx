from typing import cast

from django.db.models import Count, QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from chat.models import ChatMember, GroupChat
from chat.permissions import ReadOnlyMemberOrOwner
from chat.serializers import GroupChatSerializer
from chat.tasks import task_handle_group_chat_update, task_handle_new_group_member
from utils.request import AuthenticatedRequest


class GroupChatViewSet(ModelViewSet[GroupChat]):
    serializer_class = GroupChatSerializer
    permission_classes = [IsAuthenticated & ReadOnlyMemberOrOwner]

    queryset = GroupChat.objects.none()

    def get_queryset(self) -> QuerySet[GroupChat]:
        request = cast(AuthenticatedRequest, self.request)
        return (
            request.user.chat_groups.annotate(
                member_count=Count("members")
            )  # Optimize member count queries
            .order_by("-updated_at")
            .all()
        )

    def perform_create(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, serializer: BaseSerializer[GroupChat]
    ) -> None:
        group_chat = serializer.save()

        request = cast(AuthenticatedRequest, self.request)

        # Create chat member for the creator
        ChatMember.objects.create(
            user=request.user,
            group_chat=group_chat,
            nick_name=request.user.email,
            chat_role=ChatMember.ChatMemberRole.OWNER,
        )

        # Trigger tasks to handle WebSocket notifications
        task_handle_new_group_member(request.user.pk, group_chat.pk)

    def perform_update(self, serializer: BaseSerializer[GroupChat]) -> None:
        """Handle group chat updates and notify members via WebSockets."""
        group_chat = serializer.save()

        # Notify all members about the update
        task_handle_group_chat_update(group_chat.pk)
