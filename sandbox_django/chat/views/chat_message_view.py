from typing import cast

from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from chat.models import ChatMember, ChatMessage, GroupChat
from chat.permissions import IsGroupChatMemberNested
from chat.serializers import ChatMessageSerializer
from chat.tasks import task_handle_new_chat_message
from utils.request import AuthenticatedRequest


class ChatMessageViewSet(ModelViewSet[ChatMessage]):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated & IsGroupChatMemberNested]

    def get_queryset(self) -> QuerySet[ChatMessage]:
        return (
            ChatMessage.objects.filter(group_chat_id=self.kwargs["group_chat_pk"])
            .select_related("sender__user")
            .order_by("-id")
        )

    def perform_create(self, serializer: BaseSerializer[ChatMessage]) -> None:
        request = cast(AuthenticatedRequest, self.request)
        group_chat_id = self.kwargs["group_chat_pk"]

        # Get the group chat
        group_chat = GroupChat.objects.get(pk=group_chat_id)

        # Get the chat member
        member = ChatMember.objects.get(user=request.user, group_chat=group_chat)

        # Save message via REST
        message = serializer.save(group_chat=group_chat, sender=member)

        # Trigger the task to broadcast via WebSocket
        task_handle_new_chat_message(message.pk)
