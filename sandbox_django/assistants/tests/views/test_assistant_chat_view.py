from typing import cast
from uuid import uuid4

from django.http import HttpResponseRedirect
from django.test import TestCase
from django.urls import reverse

from accounts.factories.user import UserFactory
from test_utils.auth_api_test_case import AuthAPITestCase

from assistants.factories import AssistantConversationFactory, AssistantMessageFactory
from assistants.models import AssistantConversation


class AssistantChatViewTestCase(AuthAPITestCase):
    """Test cases for AssistantChatView (web interface) - authenticated users."""

    def setUp(self) -> None:
        super().setUp()
        self.home_url = reverse("assistant_chat")

    def test_home_page_authenticated(self) -> None:
        """Test home page for authenticated user."""
        # Create some conversations for the user
        AssistantConversationFactory.create(user=self.user, title="First Conv")
        AssistantConversationFactory.create(user=self.user, title="Second Conv")

        # Create conversation for another user (should not be included)
        other_user = UserFactory.create()
        AssistantConversationFactory.create(user=other_user, title="Other Conv")

        response = self.auth_client.get(self.home_url)

        assert response.status_code == 200
        assert response.context["is_root_page"] is True
        assert response.context["conversation"] is None
        assert response.context["is_authenticated"] is True

        # Check user's conversations are included
        conversations: list[AssistantConversation] = response.context["conversations"]
        assert len(conversations) == 2
        conversation_titles = [conv.title for conv in conversations]
        assert "First Conv" in conversation_titles
        assert "Second Conv" in conversation_titles
        assert "Other Conv" not in conversation_titles

    def test_conversation_page_authenticated_owner(self) -> None:
        """Test conversation page for authenticated user who owns the conversation."""
        conversation = AssistantConversationFactory.create(
            user=self.user, title="My Conversation"
        )

        # Add some messages
        AssistantMessageFactory.create_user_message(
            conversation=conversation, content="Hello"
        )
        AssistantMessageFactory.create_assistant_message(
            conversation=conversation, content="Hi there!"
        )

        # Create another conversation for sidebar
        AssistantConversationFactory.create(user=self.user, title="Other Conv")

        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )
        response = self.auth_client.get(conv_url)

        assert response.status_code == 200
        assert response.context["is_root_page"] is False
        assert response.context["conversation"] == conversation
        assert response.context["is_authenticated"] is True

        # Check conversations for sidebar
        conversations: list[AssistantConversation] = response.context["conversations"]
        assert len(conversations) == 2
        conversation_titles = [conv.title for conv in conversations]
        assert "My Conversation" in conversation_titles
        assert "Other Conv" in conversation_titles

    def test_conversation_page_authenticated_not_owner(self) -> None:
        """Test conversation page for authenticated user who doesn't own the conversation."""
        other_user = UserFactory.create()
        conversation = AssistantConversationFactory.create(user=other_user)

        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )
        response = cast(HttpResponseRedirect, self.auth_client.get(conv_url))

        assert response.status_code == 302
        assert response.url == reverse("assistant_chat")

    def test_conversation_page_authenticated_user_anonymous_conversation(self) -> None:
        """Test authenticated user trying to access anonymous conversation."""
        conversation = AssistantConversationFactory.create_anonymous()

        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )
        response = cast(HttpResponseRedirect, self.auth_client.get(conv_url))

        # Should redirect to home page
        assert response.status_code == 302
        assert response.url == reverse("assistant_chat")

    def test_conversation_page_nonexistent_conversation(self) -> None:
        """Test accessing non-existent conversation."""
        nonexistent_id = uuid4()
        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": nonexistent_id}
        )

        response = cast(HttpResponseRedirect, self.auth_client.get(conv_url))

        assert response.status_code == 302
        assert response.url == reverse("assistant_chat")

    def test_home_template_context(self) -> None:
        """Test that home page uses correct template and context."""
        response = self.auth_client.get(self.home_url)

        assert response.status_code == 200
        assert "assistants/home.html" in [t.name for t in response.templates]

    def test_conversation_template_context(self) -> None:
        """Test that conversation page uses correct template and context."""
        conversation = AssistantConversationFactory.create(user=self.user)
        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )

        response = self.auth_client.get(conv_url)

        assert response.status_code == 200
        assert "assistants/chat.html" in [t.name for t in response.templates]

    def test_conversation_ordering_in_sidebar(self) -> None:
        """Test that conversations in sidebar are ordered by updatedAt desc."""
        # Create conversations with different update times
        conv1 = AssistantConversationFactory.create(user=self.user, title="First")
        AssistantConversationFactory.create(user=self.user, title="Second")

        # Update conv1 to make it more recent
        conv1.save()  # This updates the updated_at field

        response = self.auth_client.get(self.home_url)

        conversations: list[AssistantConversation] = response.context["conversations"]
        assert len(conversations) == 2
        # First conversation should be the most recently updated (conv1)
        assert conversations[0].title == "First"
        assert conversations[1].title == "Second"

    def test_conversation_with_empty_title(self) -> None:
        """Test conversation page with empty title."""
        conversation = AssistantConversationFactory.create(user=self.user, title="")
        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )

        response = self.auth_client.get(conv_url)

        assert response.status_code == 200
        assert response.context["conversation"] == conversation
        assert response.context["conversation"].title == ""

    def test_multiple_conversations_ordering(self) -> None:
        """Test that multiple conversations are properly ordered in context."""
        conversations = []
        for i in range(5):
            conv = AssistantConversationFactory.create(
                user=self.user, title=f"Conv {i}"
            )
            conversations.append(conv)

        # Update middle conversation to make it most recent
        conversations[2].save()

        response = self.auth_client.get(self.home_url)

        context_conversations: list[AssistantConversation] = response.context[
            "conversations"
        ]
        assert len(context_conversations) == 5
        # Most recently updated should be first
        assert context_conversations[0].title == "Conv 2"


class AssistantChatViewUnauthenticatedTestCase(TestCase):
    """Test cases for unauthenticated users - using regular TestCase."""

    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.home_url = reverse("assistant_chat")

    def test_home_page_unauthenticated(self) -> None:
        """Test home page for unauthenticated user."""
        response = self.client.get(self.home_url)

        assert response.status_code == 200
        assert response.context["is_root_page"] is True
        assert response.context["conversation"] is None
        assert response.context["is_authenticated"] is False
        assert len(response.context["conversations"]) == 0

    def test_conversation_page_anonymous_user_anonymous_conversation(self) -> None:
        """Test anonymous user accessing anonymous conversation."""
        conversation = AssistantConversationFactory.create_anonymous(
            title="Anonymous Conv"
        )

        # Add some messages
        AssistantMessageFactory.create_user_message(
            conversation=conversation, content="Anonymous message"
        )

        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )
        response = self.client.get(conv_url)

        assert response.status_code == 200
        assert response.context["is_root_page"] is False
        assert response.context["conversation"] == conversation
        assert response.context["is_authenticated"] is False
        assert len(response.context["conversations"]) == 0  # No sidebar for anonymous

    def test_conversation_page_anonymous_user_authenticated_conversation(self) -> None:
        """Test anonymous user trying to access authenticated conversation."""
        conversation = AssistantConversationFactory.create(user=self.user)

        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": conversation.id}
        )
        response = cast(HttpResponseRedirect, self.client.get(conv_url))

        assert response.status_code == 302
        assert response.url == reverse("assistant_chat")

    def test_conversation_page_invalid_uuid(self) -> None:
        """Test accessing conversation with invalid UUID."""
        # This should result in a 404 from URL routing
        response = self.client.get("/assistants/invalid-uuid/")
        assert response.status_code == 404

    def test_conversation_page_nonexistent_conversation_anonymous(self) -> None:
        """Test anonymous user accessing non-existent conversation."""
        nonexistent_id = uuid4()
        conv_url = reverse(
            "assistant_conversation", kwargs={"conversation_id": nonexistent_id}
        )

        response = cast(HttpResponseRedirect, self.client.get(conv_url))

        # Should redirect to home page
        assert response.status_code == 302
        assert response.url == reverse("assistant_chat")

    def test_home_template_context_unauthenticated(self) -> None:
        """Test that home page uses correct template for unauthenticated users."""
        response = self.client.get(self.home_url)

        assert response.status_code == 200
        assert "assistants/home.html" in [t.name for t in response.templates]
        assert response.context["is_authenticated"] is False
