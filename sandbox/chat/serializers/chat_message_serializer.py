from typing import cast

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from chat.models import ChatMessage
from chat.serializers import ManageChatMemberSerializer
from utils.request import AuthenticatedRequest


class ChatMessageSerializer(serializers.ModelSerializer[ChatMessage]):
    sender = ManageChatMemberSerializer(read_only=True)
    is_me = SerializerMethodField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "is_me",
            "sender",
            "content",
        ]

    def get_is_me(self, obj: ChatMessage) -> bool:
        request_context = cast(AuthenticatedRequest, self.context.get("request"))
        if request_context and obj.sender:
            return bool(request_context.user == obj.sender.user)
        return False
