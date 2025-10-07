from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from assistants.models import AssistantMessage


class AssistantMessageSerializer(serializers.ModelSerializer[AssistantMessage]):
    """Serializer for assistant messages."""

    formatted_created_at = SerializerMethodField(read_only=True)

    class Meta:
        model = AssistantMessage
        fields = [
            "id",
            "content",
            "message_type",
            "created_at",
            "formatted_created_at",
        ]

    def get_formatted_created_at(self, obj: AssistantMessage) -> str:
        """Return a user-friendly time format."""
        return obj.created_at.strftime("%I:%M %p - %b %d, %Y")


class CreateAssistantMessageSerializer(serializers.ModelSerializer[AssistantMessage]):
    """Serializer for creating new assistant messages."""

    class Meta:
        model = AssistantMessage
        fields = ["content"]
