from typing import cast

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from test_utils.auth_api_test_case import AuthAPITestCase

from chat.factories.group_chat import GroupChatFactory
from chat.models import ChatMember, ChatMessage, GroupChat


class GroupChatDetailViewTestCase(AuthAPITestCase):
    """Test case for GroupChatDetailView (Chat Detail Page)."""

    def setUp(self) -> None:
        super().setUp()

        # Create a group chat that the user is a member of
        self.group_chat = GroupChatFactory.create(title="Test Chat")
        self.chat_member = ChatMember.objects.create(
            user=self.user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
            nick_name=self.user.email,
        )

        # Create some sample messages
        self.message = ChatMessage.objects.create(
            group_chat=self.group_chat,
            sender=self.chat_member,
            content="Test message content",
        )

        # URL for the detail view
        self.url = reverse("chat-group-detail", kwargs={"pk": self.group_chat.pk})

    def test_get_chat_detail_as_member(self) -> None:
        """Test that a member can access the chat detail page."""
        # Make the request
        response = self.auth_client.get(self.url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Check that the template was rendered
        assert "chat/group_chat.html" in [t.name for t in response.templates]

        # Check that the group chat is in the context
        group_chat = response.context.get("group_chat")
        assert group_chat is not None
        assert group_chat.title == "Test Chat"

        # Check that the user's chats list is in the context
        user_chats = response.context.get("user_chats")
        assert user_chats is not None
        assert len(user_chats) == 1
        assert user_chats[0].title == "Test Chat"

        # Check member status
        is_member = response.context.get("is_member")
        assert is_member is True

        user_member = response.context.get("user_member")
        assert user_member is not None
        assert user_member == self.chat_member

    def test_get_chat_detail_unauthenticated(self) -> None:
        """Test that an unauthenticated user can access the page but with limited functionality."""
        # Make the request with unauthenticated client
        response = self.client.get(self.url)

        # Verify that we get a successful response (not 401 anymore)
        assert response.status_code == status.HTTP_200_OK

        # Check that the template was rendered
        assert "chat/group_chat.html" in [t.name for t in response.templates]

        # Check that the group chat is in the context
        group_chat = response.context.get("group_chat")
        assert group_chat is not None
        assert group_chat.title == "Test Chat"

        # Check that user_chats is empty for unauthenticated users
        user_chats = response.context.get("user_chats")
        assert user_chats == []

        # Check member status
        is_member = response.context.get("is_member")
        assert is_member is False

        user_member = response.context.get("user_member")
        assert user_member is None

    def test_get_chat_detail_as_non_member(self) -> None:
        """Test that an authenticated non-member can access the page but with restricted functionality."""
        # Create a new user who is not a member of the group chat
        other_user = UserFactory.create()
        other_client = self.get_client_for_user(other_user)

        # Make the request
        response = other_client.get(self.url)

        # Verify the user can access the page (not 403 anymore)
        assert response.status_code == status.HTTP_200_OK

        # Check that the template was rendered
        assert "chat/group_chat.html" in [t.name for t in response.templates]

        # Check that the group chat is in the context
        group_chat = response.context.get("group_chat")
        assert group_chat is not None
        assert group_chat.title == "Test Chat"

        # Check member status
        is_member = response.context.get("is_member")
        assert is_member is False

        user_member = response.context.get("user_member")
        assert user_member is None

        # User chats should be empty since they're not a member of this chat
        user_chats = response.context.get("user_chats")
        assert user_chats == []

    def test_chat_detail_page_contains_required_elements_for_members(self) -> None:
        """Test that the chat detail page contains all required UI elements for members."""
        # Make the request
        response = self.auth_client.get(self.url)
        content = response.content.decode()

        # Check for important UI elements
        assert self.group_chat.title in content
        assert "My Chats" in content
        assert "Members" in content

        # Check for message-related elements
        assert "messagesContainer" in content or "messages" in content
        assert "messageForm" in content
        assert "messageInput" in content
        assert "messageTemplate" in content

        # Check for WebSocket connection elements
        assert "connectionStatus" in content
        assert "connectWebSocket" in content
        assert "socket = new WebSocket" in content
        assert f"groupId = {self.group_chat.pk}" in content

        # Check for message handling functions
        assert "loadMessages" in content
        assert "sendMessage" in content
        assert "addMessageToUI" in content

    def test_chat_detail_page_contains_login_prompt_for_unauthenticated(self) -> None:
        """Test that the chat detail page shows login prompt for unauthenticated users."""
        # Make the request with unauthenticated client
        response = self.client.get(self.url)
        content = response.content.decode()

        # Check for login-related content
        assert "Welcome to" in content
        assert "log in" in content
        # Check for the actual login URL instead of the URL name
        login_url = reverse("rest_login")
        assert login_url in content
        assert self.group_chat.title in content

        # Should not have WebSocket functionality
        assert "connectWebSocket" not in content
        assert "messageForm" not in content

    def test_chat_detail_page_shows_access_restricted_for_non_members(self) -> None:
        """Test that the chat detail page shows access restricted message for authenticated non-members."""
        # Create a new user who is not a member
        other_user = UserFactory.create()
        other_client = self.get_client_for_user(other_user)

        # Make the request
        response = other_client.get(self.url)
        content = response.content.decode()

        # Check for access restricted content
        assert "Access Restricted" in content
        assert "not a member" in content
        assert self.group_chat.title in content

        # Should not have WebSocket functionality
        assert "connectWebSocket" not in content
        assert "messageForm" not in content

    def test_chat_detail_url_with_invalid_id(self) -> None:
        """Test accessing the chat detail page with an invalid group chat ID."""
        # URL for a nonexistent group chat
        url = reverse("chat-group-detail", kwargs={"pk": 99999})

        # Make the request
        response = self.auth_client.get(url)

        # Verify response - should redirect to chat-home with error message
        assert response.status_code == status.HTTP_302_FOUND
        redirect_response = cast(HttpResponseRedirect, response)
        assert redirect_response.url == reverse("chat-home")

    def test_chat_detail_with_multiple_members(self) -> None:
        """Test chat detail page with multiple chat members."""
        # Add another user to the group chat
        other_user = UserFactory.create(email="other@mail.com")
        ChatMember.objects.create(
            user=other_user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
            nick_name=other_user.email,
        )

        # Make the request
        response = self.auth_client.get(self.url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Get the group chat object
        group_chat = cast(GroupChat, response.context.get("group_chat"))

        # Verify the group chat has two members
        assert group_chat.members.count() == 2

    def test_non_member_sees_restricted_access_elements(self) -> None:
        """Test that authenticated non-members see appropriate access restriction elements."""
        other_user = UserFactory.create()
        other_client = self.get_client_for_user(other_user)

        response = other_client.get(self.url)
        content = response.content.decode()

        # Should see access restriction message
        assert "You are not a member" in content
        assert "Contact a group administrator" in content
        assert "return to your chats" in content

    def test_member_sees_full_functionality(self) -> None:
        """Test that members see full chat functionality."""
        response = self.auth_client.get(self.url)
        content = response.content.decode()

        # Should see full chat interface
        assert "messageForm" in content
        assert "Loading messages..." in content
        assert "Type your message here..." in content
        assert "Connected" in content or "connectionStatus" in content
