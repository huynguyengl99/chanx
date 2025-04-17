from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from chat.models import ChatMessage
from chat.serializers import ManageChatMemberSerializer


class RawMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "content", "created"]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = ManageChatMemberSerializer(read_only=True)
    is_me = SerializerMethodField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "created",
            "id",
            "is_me",
            "sender",
            "content",
        ]

    def get_is_me(self, obj) -> bool:
        request_context = self.context.get("request")
        if request_context:
            return request_context.user == obj.sender.user
        return False
