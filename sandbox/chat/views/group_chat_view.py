from typing import cast

from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from chat.models import ChatMember, GroupChat
from chat.permissions import ReadOnlyMemberOrOwner
from chat.serializers import GroupChatSerializer
from chat.tasks import task_handle_new_group_chat_member
from utils.request import AuthenticatedRequest


class GroupChatViewSet(ModelViewSet[GroupChat]):
    serializer_class = GroupChatSerializer
    permission_classes = [IsAuthenticated & ReadOnlyMemberOrOwner]

    queryset = GroupChat.objects.none()

    def get_queryset(self) -> QuerySet[GroupChat]:
        request = cast(AuthenticatedRequest, self.request)
        return request.user.chat_groups.order_by("-modified").all()

    def perform_create(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, serializer: BaseSerializer[GroupChat]
    ) -> None:
        group_chat = serializer.save()

        request = cast(AuthenticatedRequest, self.request)

        ChatMember.objects.create(
            user=request.user,
            group_chat=group_chat,
            nick_name=request.user.email,
            chat_role=ChatMember.ChatMemberRole.OWNER,
        )

        task_handle_new_group_chat_member(request.user.pk, group_chat.pk)
