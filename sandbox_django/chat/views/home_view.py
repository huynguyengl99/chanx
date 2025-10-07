from typing import Any, cast

from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import ChatMember, GroupChat
from chat.tasks import task_handle_new_group_member
from utils.request import AuthenticatedRequest


class NewGroupChatForm(forms.Form):
    """Form for creating a new group chat."""

    title = forms.CharField(max_length=255, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)


# Define a type alias for the template context
TemplateContext = dict[str, Any]


class HomeView(APIView):
    """Home page view with chat list and new chat form using DRF APIView.

    This view renders HTML templates but uses REST Framework's authentication
    and permission system.
    """

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "chat/home.html"
    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        """Handle GET requests to display the home page."""
        # Create a new form
        form = NewGroupChatForm()

        # Initialize context
        context: TemplateContext = {
            "form": form,
            "user_chats": [],
        }

        # Get user's chats if authenticated
        if request.user.is_authenticated:
            request_auth = cast(AuthenticatedRequest, request)
            user_chats = GroupChat.objects.filter(
                members__user=request_auth.user
            ).order_by("-updated_at")
            context["user_chats"] = user_chats

        # Return the rendered template with context
        return Response(context)

    def post(self, request: Request) -> HttpResponse:
        """Handle POST requests to create a new group chat."""
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect(reverse("rest_login") + "?next=" + request.path)

        request_data = request.data
        form = NewGroupChatForm(request_data)

        if form.is_valid():
            request_auth = cast(AuthenticatedRequest, request)

            # Create the group chat
            group_chat = GroupChat.objects.create(
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
            )

            # Add the user as owner
            ChatMember.objects.create(
                user=request_auth.user,
                group_chat=group_chat,
                chat_role=ChatMember.ChatMemberRole.OWNER,
                nick_name=request_auth.user.email,
            )

            task_handle_new_group_member(request_auth.user.pk, group_chat.pk)

            # Redirect to the new chat
            return redirect("chat-group-detail", pk=group_chat.pk)

        # If form is invalid, re-render the template with errors
        context: TemplateContext = {
            "form": form,
            "user_chats": [],
        }

        request_auth = cast(AuthenticatedRequest, request)
        user_chats = GroupChat.objects.filter(members__user=request_auth.user).order_by(
            "-updated_at"
        )
        context["user_chats"] = user_chats

        # Return the template with the form
        return render(
            request, self.template_name, context, status=status.HTTP_400_BAD_REQUEST
        )
