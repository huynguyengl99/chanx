from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from accounts.serializers.user_serializer import EmailUserField

from chat.models import ChatMember, GroupChat


class ChatMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMember
        fields = [
            "nick_name",
            "chat_role",
        ]
        read_only_fields = [
            "chat_role",
        ]


class ManageChatMemberSerializer(serializers.ModelSerializer):
    user = EmailUserField()

    class Meta:
        model = ChatMember
        fields = ["id", "user", "chat_role"]
        extra_kwargs = {"chat_role": {"required": True}}

    def validate_role(self, value):
        if value == ChatMember.ChatMemberRole.OWNER:
            raise serializers.ValidationError("Cannot add new owner")

        return value

    def create(self, validated_data):
        group_chat = get_object_or_404(GroupChat, id=validated_data["group_chat_id"])

        member_data = {
            "user": validated_data["user"],
            "group_chat_id": validated_data["group_chat_id"],
            "nick_name": validated_data["user"].email,
            "chat_role": validated_data["chat_role"],
        }
        instance = ChatMember(**member_data)
        instance.save()
        group_chat.save(update_fields=["modified"])
        return instance
