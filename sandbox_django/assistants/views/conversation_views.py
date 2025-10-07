from typing import cast

from django.db.models import QuerySet
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import ModelViewSet

from assistants.models import AssistantConversation
from assistants.serializers import AssistantConversationSerializer
from utils.request import AuthenticatedRequest


class AssistantConversationViewSet(ModelViewSet[AssistantConversation]):
    """ViewSet for assistant conversations."""

    permission_classes = [IsAuthenticated]
    serializer_class = AssistantConversationSerializer

    def get_queryset(self) -> QuerySet[AssistantConversation]:
        """Get conversations for the authenticated user."""
        request = cast(AuthenticatedRequest, self.request)
        return AssistantConversation.objects.filter(user=request.user).order_by(
            "-updated_at"
        )

    def perform_create(self, serializer: BaseSerializer[AssistantConversation]) -> None:
        """Create conversation."""

        serializer.save(user=self.request.user)
