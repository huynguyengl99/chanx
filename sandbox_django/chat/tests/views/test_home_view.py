from typing import cast

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status

from test_utils.auth_api_test_case import AuthAPITestCase

from chat.factories.chat_member import ChatMemberFactory
from chat.factories.group_chat import GroupChatFactory
from chat.models import GroupChat


class HomeViewTestCase(AuthAPITestCase):
    """Test case for HomeView (Chat App Home Page)."""

    def setUp(self) -> None:
        super().setUp()
        self.url = reverse("chat-home")

    def test_get_home_page_authenticated(self) -> None:
        """Test that an authenticated user can access the home page with their chats."""
        # Create some group chats for the user
        group_chat1 = GroupChatFactory.create(title="Chat 1")
        group_chat2 = GroupChatFactory.create(title="Chat 2")

        ChatMemberFactory.create_owner(user=self.user, group_chat=group_chat1)

        ChatMemberFactory.create(user=self.user, group_chat=group_chat2)

        # Make the request
        response = self.auth_client.get(self.url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Check that the template was rendered
        assert "chat/home.html" in [t.name for t in response.templates]

        # Check that the user's chats are in the context
        user_chats = response.context.get("user_chats")
        assert user_chats is not None
        assert len(user_chats) == 2
        assert {chat.title for chat in user_chats} == {"Chat 1", "Chat 2"}

    def test_get_home_page_unauthenticated(self) -> None:
        """Test that an unauthenticated user can access the home page, but sees no chats."""
        # Make the request with unauthenticated client
        response = self.client.get(self.url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Check that the template was rendered
        assert "chat/home.html" in [t.name for t in response.templates]

        # Check that there are no user chats in the context
        user_chats = response.context.get("user_chats")
        assert user_chats is not None
        assert len(user_chats) == 0

    def test_post_create_chat_authenticated(self) -> None:
        """Test that an authenticated user can create a new chat."""
        # Chat data
        chat_data = {"title": "New Test Chat", "description": "This is a test chat"}

        # Make the request
        response = self.auth_client.post(self.url, chat_data)

        # Verify that we get redirected to the new chat page
        assert response.status_code == status.HTTP_302_FOUND

        # Verify the chat was created
        chat = GroupChat.objects.filter(title="New Test Chat").first()
        assert chat is not None

        # Verify we're redirected to the chat detail page
        assert cast(HttpResponseRedirect, response).url == reverse(
            "chat-group-detail", kwargs={"pk": chat.pk}
        )

        # Verify the user is an owner of the chat
        member = chat.members.get(user=self.user)
        assert member.chat_role == member.ChatMemberRole.OWNER

    def test_post_create_chat_unauthenticated(self) -> None:
        """Test that an unauthenticated user cannot create a new chat."""
        # Chat data
        chat_data = {"title": "New Test Chat", "description": "This is a test chat"}

        # Make the request with unauthenticated client
        response = self.client.post(self.url, chat_data)

        # Verify that we get redirected to the login page
        assert response.status_code == status.HTTP_302_FOUND
        assert "login" in cast(HttpResponseRedirect, response).url

        # Verify no chat was created
        assert not GroupChat.objects.filter(title="New Test Chat").exists()

    def test_form_validation(self) -> None:
        """Test form validation when creating a new chat."""
        # Empty title data
        chat_data = {"title": "", "description": "This is a test chat"}

        # Make the request
        response = self.auth_client.post(self.url, chat_data)

        # Verify response - should re-render the form with errors
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Check the form has errors
        form = response.context.get("form")
        assert form is not None
        assert form.errors
        assert "title" in form.errors

        # Verify no chat was created
        assert not GroupChat.objects.filter(description="This is a test chat").exists()

    def test_home_page_contains_required_elements(self) -> None:
        """Test that the home page contains all required UI elements."""
        response = self.auth_client.get(self.url)
        content = response.content.decode()

        # Check for important UI elements
        assert "My Group Chats" in content
        assert "New Group Chat" in content
        assert "Chat Title" in content
        assert "Create Chat" in content

        # Check for the WebSocket connection elements
        assert "connectionStatus" in content
        assert "refreshGroupChats" in content
        assert "groupChatList" in content
