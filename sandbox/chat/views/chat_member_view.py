from django.db.models import QuerySet
from rest_framework.generics import (
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from chat.models import ChatMember
from chat.permissions import GroupChatManagerOrMemberReadonly, IsGroupChatMemberNested
from chat.serializers import ChatMemberSerializer, ManageChatMemberSerializer


class ManageChatMemberViewSet(ModelViewSet[ChatMember]):
    serializer_class = ManageChatMemberSerializer
    permission_classes = [IsAuthenticated & GroupChatManagerOrMemberReadonly]

    queryset = ChatMember.objects.none()

    def get_queryset(self) -> QuerySet[ChatMember]:
        return ChatMember.objects.filter(group_chat=self.kwargs["group_chat_pk"])

    def perform_create(self, serializer: BaseSerializer[ChatMember]) -> None:
        serializer.save(
            group_chat_id=self.kwargs["group_chat_pk"],
        )


class ChatMemberView(RetrieveUpdateDestroyAPIView[ChatMember]):
    serializer_class = ChatMemberSerializer
    permission_classes = [IsAuthenticated & IsGroupChatMemberNested]

    queryset = ChatMember.objects.none()

    def get_object(self) -> ChatMember:
        group_chat_pk = self.kwargs["group_chat_pk"]
        chat_member = get_object_or_404(
            ChatMember, group_chat=group_chat_pk, user=self.request.user
        )
        return chat_member
