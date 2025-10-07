from rest_framework import serializers

from accounts.serializers.user_serializer import EmailUserField

from chat.models import ChatMember


class ManageChatMemberSerializer(serializers.ModelSerializer[ChatMember]):
    """Serializer for displaying chat member information."""

    user = EmailUserField()

    class Meta:
        model = ChatMember
        fields = ["id", "user", "chat_role", "user_id"]
