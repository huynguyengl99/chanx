from typing import cast

from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from accounts.models import User

from chat.models import ChatMember, GroupChat
from chat.permissions import ReadOnlyMemberOrOwner
from chat.serializers import GroupChatSerializer
from chat.tasks import task_handle_new_group_chat_member


class GroupChatViewSet(ModelViewSet[GroupChat]):
    serializer_class = GroupChatSerializer
    permission_classes = [IsAuthenticated & ReadOnlyMemberOrOwner]

    queryset = GroupChat.objects.none()

    def get_queryset(self) -> QuerySet[GroupChat]:
        user = cast(User, self.request.user)
        return user.chat_groups.order_by("-modified").all()

    def perform_create(self, serializer: BaseSerializer[GroupChat]) -> None:
        group_chat = serializer.save()

        user = cast(User, self.request.user)

        ChatMember.objects.create(
            user=user,
            group_chat=group_chat,
            nick_name=user.email,
            chat_role=ChatMember.ChatMemberRole.OWNER,
        )

        task_handle_new_group_chat_member(user.pk, group_chat.pk)
