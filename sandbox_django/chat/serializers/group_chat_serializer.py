from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from chat.models import GroupChat


class GroupChatSerializer(serializers.ModelSerializer[GroupChat]):
    member_count = SerializerMethodField(read_only=True)

    class Meta:
        model = GroupChat
        fields = [
            "id",
            "title",
            "description",
            "member_count",
            "updated_at",
        ]

    def get_member_count(self, obj: GroupChat) -> int:
        """Get the number of members in this group chat."""
        return obj.members.count()
