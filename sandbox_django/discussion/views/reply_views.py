from typing import Any, cast

from django.db import transaction
from django.db.models import F, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from discussion.models import DiscussionReply, DiscussionTopic
from discussion.serializers.reply_serializers import (
    CreateDiscussionReplySerializer,
    DiscussionReplySerializer,
)
from discussion.serializers.voting_serializers import VoteSerializer
from discussion.tasks import (
    task_broadcast_new_reply,
    task_broadcast_vote_update,
)
from utils.request import AuthenticatedRequest


class DiscussionReplyViewSet(ModelViewSet[DiscussionReply]):
    """ViewSet for discussion replies."""

    permission_classes = [IsAuthenticated]
    serializer_class = DiscussionReplySerializer

    def get_queryset(self) -> QuerySet[DiscussionReply]:
        topic_pk = self.kwargs.get("topic_pk")
        if not topic_pk:
            return DiscussionReply.objects.none()

        return (
            DiscussionReply.objects.filter(topic_id=topic_pk)
            .select_related("author", "topic")
            .order_by("-vote_count", "created_at")
        )

    def get_serializer_class(self) -> type[BaseSerializer[DiscussionReply]]:
        if self.action == "create":
            return CreateDiscussionReplySerializer
        return DiscussionReplySerializer

    def perform_create(self, serializer: BaseSerializer[DiscussionReply]) -> None:
        """Create a new reply and broadcast it."""
        request = cast(AuthenticatedRequest, self.request)
        topic_pk = self.kwargs.get("topic_pk")
        topic = get_object_or_404(DiscussionTopic, pk=topic_pk)

        reply = serializer.save(author=request.user, topic=topic)

        # Broadcast new reply via WebSocket
        task_broadcast_new_reply(reply.pk)

    @action(detail=True, methods=["post"], url_path="vote")
    def vote_on_reply(self, request: Request, **kwargs: Any) -> Response:
        """Vote on a reply."""
        reply = self.get_object()

        vote_serializer = VoteSerializer(data=request.data)
        if not vote_serializer.is_valid():
            return Response(vote_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vote_value = vote_serializer.validated_data["vote"]

        with transaction.atomic():
            # Update the reply's vote count
            reply.vote_count = F("vote_count") + vote_value
            reply.save(update_fields=["vote_count"])

        # Refresh reply to get updated vote count
        reply.refresh_from_db()

        # Broadcast vote update
        task_broadcast_vote_update("reply", reply.pk, reply.vote_count)

        return Response(
            {
                "vote": vote_value,
                "vote_count": reply.vote_count,
            }
        )
