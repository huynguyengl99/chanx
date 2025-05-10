from rest_framework import serializers

from chat.models import GroupChat


class GroupChatSerializer(serializers.ModelSerializer[GroupChat]):
    class Meta:
        model = GroupChat
        fields = [
            "id",
            "title",
            "description",
        ]
