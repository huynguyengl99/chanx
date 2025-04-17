from rest_framework import serializers

from chat.models import GroupChat


class GroupChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupChat
        fields = [
            "id",
            "title",
            "description",
            "created",
            "modified",
        ]
