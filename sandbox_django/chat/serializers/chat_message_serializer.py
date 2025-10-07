from typing import cast

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from chat.models import ChatMessage
from chat.serializers import ManageChatMemberSerializer
from utils.request import AuthenticatedRequest


class ChatMessageSerializer(serializers.ModelSerializer[ChatMessage]):
    sender = ManageChatMemberSerializer(read_only=True)
    is_mine = SerializerMethodField(read_only=True)
    formatted_time = SerializerMethodField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "is_mine",
            "sender",
            "content",
            "created_at",
            "formatted_time",
            "updated_at",
            "is_edited",
        ]

    def get_is_mine(self, obj: ChatMessage) -> bool:
        request_context = cast(AuthenticatedRequest, self.context.get("request"))
        if request_context and obj.sender:
            return bool(request_context.user == obj.sender.user)
        return False

    def get_formatted_time(self, obj: ChatMessage) -> str:
        """Return a user-friendly time format."""
        return obj.created_at.strftime("%I:%M %p - %b %d, %Y")
