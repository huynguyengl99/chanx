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
from discussion.serializers.topic_serializers import (
    CreateDiscussionTopicSerializer,
    DiscussionTopicDetailSerializer,
    DiscussionTopicListSerializer,
)
from discussion.serializers.voting_serializers import VoteSerializer
from discussion.tasks import (
    task_broadcast_answer_accepted,
    task_broadcast_answer_unaccepted,
    task_broadcast_new_topic,
    task_broadcast_vote_update,
)
from utils.request import AuthenticatedRequest


class DiscussionTopicViewSet(ModelViewSet[DiscussionTopic]):
    """ViewSet for discussion topics."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[DiscussionTopic]:
        return (
            DiscussionTopic.objects.select_related("author", "accepted_answer__author")
            .prefetch_related("replies__author")
            .order_by("-created_at")
        )

    def get_serializer_class(self) -> type[BaseSerializer[DiscussionTopic]]:
        if self.action == "list":
            return DiscussionTopicListSerializer
        elif self.action == "create":
            return CreateDiscussionTopicSerializer
        else:
            return DiscussionTopicDetailSerializer

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retrieve a topic and increment view count."""
        instance = self.get_object()

        # Increment view count
        DiscussionTopic.objects.filter(pk=instance.pk).update(
            view_count=F("view_count") + 1
        )

        # Refresh instance to get updated view count
        instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer: BaseSerializer[DiscussionTopic]) -> None:
        """Create a new topic and broadcast it."""
        request = cast(AuthenticatedRequest, self.request)
        topic = serializer.save(author=request.user)

        # Broadcast new topic via WebSocket
        task_broadcast_new_topic(topic.pk)

    @action(detail=True, methods=["post"], url_path="vote")
    def vote_on_topic(self, request: Request, pk: str | None = None) -> Response:
        """Vote on a topic."""
        topic = self.get_object()

        vote_serializer = VoteSerializer(data=request.data)
        if not vote_serializer.is_valid():
            return Response(vote_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vote_value = vote_serializer.validated_data["vote"]

        with transaction.atomic():
            # Update the topic's vote count
            topic.vote_count = F("vote_count") + vote_value
            topic.save(update_fields=["vote_count"])

        # Refresh topic to get updated vote count
        topic.refresh_from_db()

        # Broadcast vote update
        task_broadcast_vote_update("topic", topic.pk, topic.vote_count)

        return Response(
            {
                "vote": vote_value,
                "vote_count": topic.vote_count,
            }
        )

    @action(detail=True, methods=["post"], url_path="accept-answer")
    def accept_answer(self, request: Request, pk: str | None = None) -> Response:
        """Accept a reply as the answer for this topic."""
        topic = self.get_object()
        request_auth = cast(AuthenticatedRequest, request)

        # Only topic author can accept answers
        if topic.author != request_auth.user:
            return Response(
                {"detail": "Only the topic author can accept answers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reply_id = request.data.get("reply_id")
        if not reply_id:
            return Response(
                {"detail": "reply_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        reply = get_object_or_404(
            DiscussionReply.objects.select_related("author"),
            pk=reply_id,
            topic=topic,
        )

        # Don't allow accepting your own answer
        if reply.author == request_auth.user:
            return Response(
                {"detail": "You cannot accept your own answer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update topic's accepted answer
        with transaction.atomic():
            topic.accepted_answer = reply
            topic.save(update_fields=["accepted_answer"])

        # Broadcast answer acceptance
        task_broadcast_answer_accepted(topic.pk, reply.pk)

        return Response({"detail": "Answer accepted successfully."})

    @action(detail=True, methods=["post"], url_path="unaccept-answer")
    def unaccept_answer(self, request: Request, pk: str | None = None) -> Response:
        """Unaccept the current accepted answer for this topic."""
        topic = self.get_object()
        request_auth = cast(AuthenticatedRequest, request)

        # Only topic author can unaccept answers
        if topic.author != request_auth.user:
            return Response(
                {"detail": "Only the topic author can unaccept answers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if there's an accepted answer
        if not topic.accepted_answer:
            return Response(
                {"detail": "No answer is currently accepted for this topic."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store the reply ID for broadcasting before clearing it
        reply_id = topic.accepted_answer.pk

        # Update topic's accepted answer to None
        with transaction.atomic():
            topic.accepted_answer = None
            topic.save(update_fields=["accepted_answer"])

        # Broadcast answer unacceptance
        task_broadcast_answer_unaccepted(topic.pk, reply_id)

        return Response({"detail": "Answer unaccepted successfully."})
