from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from chat.models import ChatMember, GroupChat
from chat.permissions import ReadOnlyMemberOrOwner
from chat.serializers import GroupChatSerializer
from chat.tasks import task_handle_new_group_chat_member


class GroupChatViewSet(ModelViewSet):
    serializer_class = GroupChatSerializer
    permission_classes = [IsAuthenticated & ReadOnlyMemberOrOwner]

    queryset = GroupChat.objects.none()

    def get_queryset(self):
        return self.request.user.chat_groups.order_by("-modified").all()

    def perform_create(self, serializer):
        group_chat = serializer.save()

        ChatMember.objects.create(
            user=self.request.user,
            group_chat=group_chat,
            nick_name=self.request.user.email,
            chat_role=ChatMember.ChatMemberRole.OWNER,
        )

        task_handle_new_group_chat_member(self.request.user.id, group_chat.id)
