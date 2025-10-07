from typing import Any

from rest_framework import serializers


class VoteSerializer(serializers.Serializer[dict[str, Any]]):
    """Simplified serializer for voting - just indicates up or down."""

    # Use int field: 1 for upvote, -1 for downvote
    vote = serializers.IntegerField(min_value=-1, max_value=1)
