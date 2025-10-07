from typing import Any, cast

from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import ChatMember, GroupChat
from utils.request import AuthenticatedRequest


class GroupChatDetailView(APIView):
    """View for the chat interface using DRF APIView."""

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "chat/group_chat.html"
    permission_classes = [AllowAny]

    def get(self, request: Request, pk: int) -> Response | HttpResponseRedirect:
        """Handle GET requests to display the chat interface."""
        # Try to get the group chat, redirect to home with message if not found
        try:
            group_chat = GroupChat.objects.get(pk=pk)
        except GroupChat.DoesNotExist:
            # Convert DRF request to Django request for messages
            django_request = cast(HttpRequest, request)
            messages.error(
                django_request,
                "Chat not found. The chat you're looking for doesn't exist or may have been removed.",
            )
            return redirect("chat-home")

        # Initialize context with proper typing
        context: dict[str, Any] = {
            "group_chat": group_chat,
            "user_chats": [],
            "is_member": False,
            "user_member": None,
        }

        # Check if user is authenticated and a member
        if request.user.is_authenticated:
            request_auth = cast(AuthenticatedRequest, request)

            # Check if user is a member of this chat
            try:
                user_member = ChatMember.objects.get(
                    user=request_auth.user, group_chat=group_chat
                )
                context["is_member"] = True
                context["user_member"] = user_member

                # Get all user's chats for the sidebar
                user_chats = GroupChat.objects.filter(
                    members__user=request_auth.user
                ).order_by("title")
                context["user_chats"] = list(user_chats)

            except ChatMember.DoesNotExist:
                # User is authenticated but not a member
                context["is_member"] = False

        # Return the rendered template with context
        return Response(context)
