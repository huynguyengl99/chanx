from typing import Any, cast

from django.contrib import messages
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from discussion.models import DiscussionTopic
from discussion.serializers.topic_serializers import CreateDiscussionTopicSerializer
from discussion.tasks import task_broadcast_new_topic
from utils.request import AuthenticatedRequest


class DiscussionHomeView(APIView):
    """Home page view for discussions with topic list."""

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "discussion/home.html"
    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        """Handle GET requests to display the discussion home page."""
        # Initialize context
        context: dict[str, Any] = {
            "recent_topics": [],
        }

        # Get recent topics for display only if user is authenticated
        if request.user.is_authenticated:
            recent_topics = (
                DiscussionTopic.objects.select_related("author")
                .prefetch_related("replies")
                .order_by("-created_at")[:20]
            )
            context["recent_topics"] = recent_topics

        return Response(context)


class NewDiscussionTopicView(APIView):
    """View for creating new discussion topics."""

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "discussion/new_topic.html"
    permission_classes = [AllowAny]  # Changed from IsAuthenticated to AllowAny

    def get(self, request: HttpRequest) -> Response:
        """Handle GET requests to display the new topic form."""
        return Response({})

    def post(self, request: Request) -> HttpResponse:
        """Handle POST requests to create a new topic."""
        # Check if user is authenticated for POST operations
        if not request.user.is_authenticated:
            # Redirect to login with next parameter
            login_url = reverse("rest_login")
            next_url = request.path
            return redirect(f"{login_url}?next={next_url}")

        request_auth = cast(AuthenticatedRequest, request)

        serializer = CreateDiscussionTopicSerializer(data=request.data)
        if serializer.is_valid():
            # Create the topic
            topic = serializer.save(author=request_auth.user)

            # Broadcast the new topic
            task_broadcast_new_topic(topic.pk)

            # Redirect to the new topic
            return redirect("discussion-detail", pk=topic.pk)

        # If serializer is invalid, re-render with errors
        return Response(
            {"errors": serializer.errors}, template_name=self.template_name, status=400
        )


class DiscussionTopicDetailView(APIView):
    """Detail view for a specific discussion topic."""

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "discussion/topic_detail.html"
    permission_classes = [AllowAny]

    def get_django_request(self, request: Request) -> HttpRequest:
        """Helper method to get Django HttpRequest for messages."""
        return cast(HttpRequest, request)

    def add_message(self, request: Request, level: int, message: str) -> None:
        """Helper method to add messages to the request."""
        django_request = self.get_django_request(request)
        messages.add_message(django_request, level, message)

    def get(self, request: Request, pk: int) -> Response | HttpResponseRedirect:
        """Handle GET requests to display topic details."""
        # Try to get the topic, redirect to home with message if not found
        try:
            topic = (
                DiscussionTopic.objects.select_related(
                    "author", "accepted_answer__author"
                )
                .prefetch_related("replies__author")
                .get(pk=pk)
            )
        except DiscussionTopic.DoesNotExist:
            self.add_message(
                request,
                messages.ERROR,
                "Discussion not found. The discussion you're looking for doesn't exist or may have been removed.",
            )
            return redirect("discussion-home")

        # Initialize context
        context: dict[str, Any] = {
            "topic": topic,
            "replies": [],
        }

        # Only show replies and increment view count if user is authenticated
        if request.user.is_authenticated:
            # Increment view count only for authenticated users
            DiscussionTopic.objects.filter(pk=pk).update(
                view_count=models.F("view_count") + 1
            )

            # Get all replies, ordered by votes then creation date
            replies = topic.replies.order_by("-vote_count", "created_at")
            context["replies"] = replies

            # Refresh topic instance to get updated view count
            topic.refresh_from_db()
            context["topic"] = topic

        return Response(context)
