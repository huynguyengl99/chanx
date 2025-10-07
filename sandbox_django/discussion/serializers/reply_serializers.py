from typing import cast

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from accounts.serializers.user_serializer import UserSerializer

from discussion.models import DiscussionReply
from utils.request import AuthenticatedRequest


class DiscussionReplySerializer(serializers.ModelSerializer[DiscussionReply]):
    """Serializer for replies."""

    author = UserSerializer(read_only=True)
    is_accepted = SerializerMethodField(read_only=True)
    formatted_created_at = SerializerMethodField(read_only=True)
    can_accept = SerializerMethodField(read_only=True)

    class Meta:
        model = DiscussionReply
        fields = [
            "id",
            "content",
            "author",
            "vote_count",
            "is_accepted",
            "created_at",
            "formatted_created_at",
            "can_accept",
        ]

    def get_is_accepted(self, obj: DiscussionReply) -> bool:
        return obj.is_accepted

    def get_formatted_created_at(self, obj: DiscussionReply) -> str:
        return obj.created_at.strftime("%b %d, %Y at %I:%M %p")

    def get_can_accept(self, obj: DiscussionReply) -> bool:
        """Check if current user can accept this answer."""
        request_context = cast(AuthenticatedRequest | None, self.context.get("request"))
        if not request_context or not request_context.user.is_authenticated:
            return False

        # Only topic author can accept answers, and not their own answers
        return (
            obj.topic.author.pk == request_context.user.pk
            and obj.author.pk != request_context.user.pk
        )


class CreateDiscussionReplySerializer(serializers.ModelSerializer[DiscussionReply]):
    """Serializer for creating new replies."""

    class Meta:
        model = DiscussionReply
        fields = ["content"]
