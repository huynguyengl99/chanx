from typing import Any, cast
from uuid import UUID

from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from assistants.models import AssistantConversation
from utils.request import AuthenticatedRequest


class AssistantChatView(APIView):
    """View for the assistant chat interface."""

    renderer_classes = [TemplateHTMLRenderer]
    permission_classes = [AllowAny]

    def get(
        self, request: HttpRequest, conversation_id: UUID | None = None
    ) -> Response | HttpResponseRedirect:
        """Handle GET requests to display the chat interface."""

        if conversation_id is None:
            # Root page - show conversation list for authenticated users
            # or simple welcome page for anonymous users
            return self.handle_root_page(request)
        else:
            # Specific conversation page
            return self.handle_conversation_page(request, conversation_id)

    def handle_root_page(self, request: HttpRequest) -> Response:
        """Handle the root assistant page (/assistants/)."""
        context: dict[str, Any] = {
            "is_root_page": True,
            "conversation": None,
            "conversations": [],
            "is_authenticated": request.user.is_authenticated,
        }

        if request.user.is_authenticated:
            request_auth = cast(AuthenticatedRequest, request)
            # Get user's conversations for sidebar
            conversations = AssistantConversation.objects.filter(
                user=request_auth.user
            ).order_by("-updated_at")
            context["conversations"] = conversations

        return Response(context, template_name="assistants/home.html")

    def handle_conversation_page(
        self, request: HttpRequest, conversation_id: UUID
    ) -> Response | HttpResponseRedirect:
        """Handle specific conversation page (/assistants/<id>/)."""

        # Get conversation or redirect if not found
        try:
            conversation = AssistantConversation.objects.get(id=conversation_id)
        except AssistantConversation.DoesNotExist:
            return redirect("assistant_chat")

        # Check access permissions
        if not self._has_conversation_access(request, conversation):
            return redirect("assistant_chat")

        # Build context
        context: dict[str, Any] = {
            "is_root_page": False,
            "conversation": conversation,
            "conversations": self._get_user_conversations(request),
            "is_authenticated": request.user.is_authenticated,
        }

        return Response(context, template_name="assistants/chat.html")

    def _has_conversation_access(
        self, request: HttpRequest, conversation: AssistantConversation
    ) -> bool:
        """Check if the current user has access to the conversation."""
        if request.user.is_authenticated:
            # Authenticated users can only access their own conversations
            return conversation.user == request.user
        else:
            # Unauthenticated users can only access anonymous conversations
            return conversation.user is None

    def _get_user_conversations(
        self, request: HttpRequest
    ) -> list[AssistantConversation]:
        """Get conversations for sidebar (only for authenticated users)."""
        if request.user.is_authenticated:
            request_auth = cast(AuthenticatedRequest, request)
            return list(
                AssistantConversation.objects.filter(user=request_auth.user).order_by(
                    "-updated_at"
                )
            )
        return []
