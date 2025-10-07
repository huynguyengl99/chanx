from rest_framework import serializers

from assistants.models import AssistantConversation


class AssistantConversationSerializer(
    serializers.ModelSerializer[AssistantConversation]
):
    """Serializer for assistant conversations."""

    class Meta:
        model = AssistantConversation
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
        ]
