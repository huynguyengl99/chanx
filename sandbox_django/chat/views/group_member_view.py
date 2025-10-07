from typing import Any, cast

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from chat.models import ChatMember, GroupChat
from chat.tasks import (
    task_handle_new_group_member,
    task_handle_remove_group_member,
)
from utils.request import AuthenticatedRequest


class GroupMemberManagementView(APIView):
    """View to manage group chat members using DRF APIView."""

    renderer_classes = [TemplateHTMLRenderer]
    template_name = "chat/group_members.html"
    permission_classes = [AllowAny]

    def get_django_request(self, request: Request) -> HttpRequest:
        """Helper method to get Django HttpRequest for messages."""
        return cast(HttpRequest, request)

    def add_message(self, request: Request, level: int, message: str) -> None:
        """Helper method to add messages to the request."""
        django_request = self.get_django_request(request)
        messages.add_message(django_request, level, message)

    def get(self, request: Request, pk: int) -> Response | HttpResponseRedirect:
        """Handle GET requests to display group members."""
        # Try to get the group chat, redirect to home with message if not found
        try:
            group_chat = GroupChat.objects.get(pk=pk)
        except GroupChat.DoesNotExist:
            self.add_message(
                request,
                messages.ERROR,
                "Chat not found. The chat you're looking for doesn't exist or may have been removed.",
            )
            return redirect("chat-home")

        # Initialize context with proper typing
        context: dict[str, Any] = {
            "group_chat": group_chat,
            "members": [],
            "user_member": None,
            "can_manage": False,
            "is_member": False,
            "roles": ChatMember.ChatMemberRole,
        }

        # Check if user is authenticated and has permissions
        if request.user.is_authenticated:
            request_auth = cast(AuthenticatedRequest, request)

            try:
                # Check if user is a member of this chat
                user_member = ChatMember.objects.get(
                    user=request_auth.user, group_chat=group_chat
                )
                context["is_member"] = True
                context["user_member"] = user_member

                # Check if user can manage members (admin or owner)
                can_manage = user_member.chat_role <= ChatMember.ChatMemberRole.ADMIN
                context["can_manage"] = can_manage

                # Get all members if user is a member
                context["members"] = list(
                    group_chat.members.select_related("user").all()
                )

            except ChatMember.DoesNotExist:
                # User is authenticated but not a member
                context["is_member"] = False

        # Return the rendered template with context
        return Response(context)

    def post(self, request: Request, pk: int) -> HttpResponseRedirect:
        """Handle POST requests to add a new member."""
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect(reverse("rest_login") + "?next=" + request.path)

        # Try to get the group chat, redirect to home with message if not found
        try:
            group_chat = GroupChat.objects.get(pk=pk)
        except GroupChat.DoesNotExist:
            self.add_message(
                request,
                messages.ERROR,
                "Chat not found. The chat you're looking for doesn't exist or may have been removed.",
            )
            return redirect("chat-home")

        request_auth = cast(AuthenticatedRequest, request)

        # Check if user is a member and can manage
        try:
            user_member = ChatMember.objects.get(
                user=request_auth.user, group_chat=group_chat
            )
            if user_member.chat_role > ChatMember.ChatMemberRole.ADMIN:
                self.add_message(
                    request, messages.ERROR, "You don't have permission to add members"
                )
                return redirect("group_members", pk=group_chat.pk)
        except ChatMember.DoesNotExist:
            self.add_message(
                request, messages.ERROR, "You are not a member of this group chat"
            )
            return redirect("chat-home")

        # Process the form
        data = request.data
        email = str(data.get("email", ""))
        role_value = data.get("role", ChatMember.ChatMemberRole.MEMBER)
        role = int(role_value)

        # Don't allow adding owners
        if role == ChatMember.ChatMemberRole.OWNER:
            self.add_message(request, messages.ERROR, "Cannot add new owners")
            return redirect("group_members", pk=group_chat.pk)

        try:
            # Find the user by email
            user = User.objects.get(email=email)

            # Create the chat member
            ChatMember.objects.create(
                user=user,
                group_chat=group_chat,
                chat_role=role,
                nick_name=user.email,
            )

            # Trigger task to handle WebSocket notification
            task_handle_new_group_member(user.pk, group_chat.pk)

            self.add_message(
                request, messages.SUCCESS, f"Added {user.email} to the group chat"
            )
        except User.DoesNotExist:
            self.add_message(
                request, messages.ERROR, f"User with email {email} not found"
            )
        except IntegrityError:
            self.add_message(
                request,
                messages.ERROR,
                f"User {email} is already a member of this group chat",
            )

        return redirect("group_members", pk=group_chat.pk)


class RemoveMemberView(APIView):
    """View to remove a member from a group chat using DRF APIView."""

    permission_classes = [AllowAny]

    def get_django_request(self, request: Request) -> HttpRequest:
        """Helper method to get Django HttpRequest for messages."""
        return cast(HttpRequest, request)

    def add_message(self, request: Request, level: int, message: str) -> None:
        """Helper method to add messages to the request."""
        django_request = self.get_django_request(request)
        messages.add_message(django_request, level, message)

    def _validate_remove_permissions(
        self, request: Request, group_chat: GroupChat, member_to_remove: ChatMember
    ) -> tuple[bool, HttpResponseRedirect | None]:
        """
        Validate if the current user can remove the specified member.

        Returns:
            (is_valid, redirect_response): If is_valid is False, redirect_response contains the error redirect.
        """
        request_auth = cast(AuthenticatedRequest, request)

        try:
            user_member = ChatMember.objects.get(
                user=request_auth.user, group_chat=group_chat
            )
        except ChatMember.DoesNotExist:
            self.add_message(
                request, messages.ERROR, "You are not a member of this group chat"
            )
            return False, redirect("chat-home")

        # Check if user has sufficient permissions (admin or owner)
        if user_member.chat_role > ChatMember.ChatMemberRole.ADMIN:
            self.add_message(
                request,
                messages.ERROR,
                "You don't have permission to remove members",
            )
            return False, redirect("group_members", pk=group_chat.pk)

        # Check if trying to remove an owner
        if member_to_remove.chat_role == ChatMember.ChatMemberRole.OWNER:
            self.add_message(request, messages.ERROR, "Cannot remove the group owner")
            return False, redirect("group_members", pk=group_chat.pk)

        return True, None

    def get(self, request: Request, pk: int, member_id: int) -> HttpResponseRedirect:
        """Handle GET requests to remove a member."""
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect(reverse("rest_login") + "?next=" + request.path)

        # Get the group chat or redirect with error message
        try:
            group_chat = GroupChat.objects.get(pk=pk)
        except GroupChat.DoesNotExist:
            self.add_message(
                request,
                messages.ERROR,
                "Chat not found. The chat you're looking for doesn't exist or may have been removed.",
            )
            return redirect("chat-home")

        # Get the member to remove or redirect with error message
        member_to_remove = get_object_or_404(
            ChatMember, pk=member_id, group_chat=group_chat
        )

        # Validate permissions
        is_valid, error_redirect = self._validate_remove_permissions(
            request, group_chat, member_to_remove
        )
        if not is_valid and error_redirect is not None:
            return error_redirect

        # Save user info before deletion
        user_id = member_to_remove.user.pk
        user_email = member_to_remove.user.email

        # Remove the member
        member_to_remove.delete()

        # Trigger task to handle WebSocket notification
        task_handle_remove_group_member(user_id, group_chat.pk)

        # Add success message and redirect
        self.add_message(
            request, messages.SUCCESS, f"Removed {user_email} from the group chat"
        )
        return redirect("group_members", pk=group_chat.pk)
