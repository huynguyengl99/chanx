from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from assistants.models import AssistantConversation


@api_view(["POST"])
@permission_classes([AllowAny])
def create_anonymous_conversation(request: Request) -> Response:
    """Create a new anonymous conversation (not tied to any user)."""

    try:
        # Create an anonymous conversation
        conversation = AssistantConversation.objects.create(
            user=None,  # Anonymous conversation
            title="",  # Will be generated from first message
        )

        return Response(
            {
                "id": str(conversation.id),
                "title": conversation.title or "New Anonymous Chat",
                "is_anonymous": True,
                "created_at": conversation.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to create anonymous conversation: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
