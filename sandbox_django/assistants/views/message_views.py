from typing import cast

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from assistants.models import AssistantConversation, AssistantMessage
from assistants.serializers import (
    AssistantMessageSerializer,
)
from assistants.tasks import task_handle_new_assistant_message
from utils.request import AuthenticatedRequest


class AssistantMessageViewSet(ModelViewSet[AssistantMessage]):
    """ViewSet for assistant messages - handles both authenticated and anonymous routes."""

    permission_classes = [AllowAny]
    serializer_class = AssistantMessageSerializer

    # Only allow read and create operations
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> QuerySet[AssistantMessage]:
        """Get messages for the conversation."""
        conversation_id = self.kwargs.get("conversation_pk")
        if not conversation_id:
            return AssistantMessage.objects.none()

        if self.request.user.is_authenticated:
            # Authenticated user - try to get their conversation
            request = cast(AuthenticatedRequest, self.request)
            conversation = get_object_or_404(
                AssistantConversation, id=conversation_id, user=request.user
            )
        else:
            # Anonymous user - try to get anonymous conversation
            conversation = get_object_or_404(
                AssistantConversation, id=conversation_id, user__isnull=True
            )

        return conversation.messages.order_by("created_at")

    def perform_create(self, serializer: BaseSerializer[AssistantMessage]) -> None:
        """Create a new user message and trigger AI response."""
        conversation_id = self.kwargs.get("conversation_pk")
        if not conversation_id:
            raise ValueError("conversation_pk is required")

        try:
            if self.request.user.is_authenticated:
                # Authenticated user - get their conversation
                request = cast(AuthenticatedRequest, self.request)
                conversation = AssistantConversation.objects.get(
                    id=conversation_id, user=request.user
                )
            else:
                # Anonymous user - get anonymous conversation
                conversation = AssistantConversation.objects.get(
                    id=conversation_id, user__isnull=True
                )

            # Save the user message
            user_message = serializer.save(
                conversation=conversation,
                message_type=AssistantMessage.MessageType.USER,
            )

            # Generate title if this is the first message
            if conversation.messages.count() == 1:
                conversation.generate_title_from_first_message()

            # Trigger async task to generate AI response
            task_handle_new_assistant_message(user_message_id=user_message.pk)

        except AssistantConversation.DoesNotExist:
            raise ValidationError("Conversation not found or access denied") from None
