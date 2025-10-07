from typing import cast

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from accounts.serializers.user_serializer import UserSerializer

from discussion.models import DiscussionTopic
from discussion.serializers.reply_serializers import DiscussionReplySerializer
from utils.request import AuthenticatedRequest


class DiscussionTopicListSerializer(serializers.ModelSerializer[DiscussionTopic]):
    """Serializer for topic list view."""

    author = UserSerializer(read_only=True)
    reply_count = SerializerMethodField(read_only=True)
    has_accepted_answer = SerializerMethodField(read_only=True)
    formatted_created_at = SerializerMethodField(read_only=True)

    class Meta:
        model = DiscussionTopic
        fields = [
            "id",
            "title",
            "author",
            "vote_count",
            "reply_count",
            "has_accepted_answer",
            "view_count",
            "created_at",
            "formatted_created_at",
        ]

    def get_reply_count(self, obj: DiscussionTopic) -> int:
        return obj.reply_count

    def get_has_accepted_answer(self, obj: DiscussionTopic) -> bool:
        return obj.accepted_answer is not None

    def get_formatted_created_at(self, obj: DiscussionTopic) -> str:
        return obj.created_at.strftime("%b %d, %Y at %I:%M %p")


class DiscussionTopicDetailSerializer(serializers.ModelSerializer[DiscussionTopic]):
    """Serializer for topic detail view."""

    author = UserSerializer(read_only=True)
    reply_count = SerializerMethodField(read_only=True)
    replies = DiscussionReplySerializer(many=True, read_only=True)
    formatted_created_at = SerializerMethodField(read_only=True)
    can_edit = SerializerMethodField(read_only=True)

    class Meta:
        model = DiscussionTopic
        fields = [
            "id",
            "title",
            "content",
            "author",
            "vote_count",
            "reply_count",
            "view_count",
            "created_at",
            "formatted_created_at",
            "accepted_answer",
            "replies",
            "can_edit",
        ]

    def get_reply_count(self, obj: DiscussionTopic) -> int:
        return obj.reply_count

    def get_formatted_created_at(self, obj: DiscussionTopic) -> str:
        return obj.created_at.strftime("%b %d, %Y at %I:%M %p")

    def get_can_edit(self, obj: DiscussionTopic) -> bool:
        """Check if current user can edit this topic."""
        request_context = cast(AuthenticatedRequest | None, self.context.get("request"))
        if not request_context or not request_context.user.is_authenticated:
            return False

        # Use .pk instead of author_id for better type safety
        return obj.author.pk == request_context.user.pk


class CreateDiscussionTopicSerializer(serializers.ModelSerializer[DiscussionTopic]):
    """Serializer for creating new topics."""

    class Meta:
        model = DiscussionTopic
        fields = ["title", "content"]
