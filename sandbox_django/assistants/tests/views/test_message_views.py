from typing import Any
from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory

import pytest
from accounts.factories.user import UserFactory
from accounts.models import User
from test_utils.auth_api_test_case import AuthAPITestCase

from assistants.factories import AssistantConversationFactory, AssistantMessageFactory
from assistants.models import AssistantConversation, AssistantMessage
from assistants.serializers import CreateAssistantMessageSerializer
from assistants.views.message_views import AssistantMessageViewSet


class AssistantMessageViewSetTestCase(AuthAPITestCase):
    """Test cases for AssistantMessageViewSet."""

    def setUp(self) -> None:
        super().setUp()
        self.conversation: AssistantConversation = AssistantConversationFactory.create(
            user=self.user
        )
        self.messages_url = reverse(
            "conversation-messages-list",
            kwargs={"conversation_pk": self.conversation.pk},
        )
        self.factory = APIRequestFactory()

    def test_list_messages_authenticated(self) -> None:
        """Test listing messages for authenticated user's conversation."""
        AssistantMessageFactory.create_user_message(
            conversation=self.conversation, content="First message"
        )
        AssistantMessageFactory.create_assistant_message(
            conversation=self.conversation, content="AI response"
        )

        response = self.auth_client.get(self.messages_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["content"] == "First message"
        assert data["results"][1]["content"] == "AI response"

    def test_list_messages_not_owner(self) -> None:
        """Test user cannot list messages from conversation they don't own."""
        other_user: User = UserFactory.create()
        other_conversation: AssistantConversation = AssistantConversationFactory.create(
            user=other_user
        )
        other_messages_url = reverse(
            "conversation-messages-list",
            kwargs={"conversation_pk": other_conversation.pk},
        )

        response = self.auth_client.get(other_messages_url)

        # Should return empty results since user doesn't own the conversation
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_messages_anonymous_conversation(self) -> None:
        """Test listing messages from anonymous conversation."""
        anon_conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )
        AssistantMessageFactory.create_user_message(
            conversation=anon_conversation, content="Anonymous message"
        )

        anon_messages_url = reverse(
            "anonymous-messages-list", kwargs={"conversation_pk": anon_conversation.pk}
        )

        response = self.client.get(anon_messages_url)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == "Anonymous message"

    def test_list_messages_anonymous_conversation_authenticated_user(self) -> None:
        """Test authenticated user cannot access anonymous conversation via anonymous route."""
        anon_conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )
        anon_messages_url = reverse(
            "anonymous-messages-list", kwargs={"conversation_pk": anon_conversation.pk}
        )

        response = self.auth_client.get(anon_messages_url)

        # Should return empty results since authenticated users accessing anonymous route
        # will not find conversations that belong to them (anonymous conversations have user=None)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_messages_unauthenticated_user_authenticated_conversation(
        self,
    ) -> None:
        """Test unauthenticated user cannot access authenticated conversation."""
        # Try to access authenticated conversation via anonymous route
        auth_messages_url = reverse(
            "anonymous-messages-list", kwargs={"conversation_pk": self.conversation.pk}
        )

        response = self.client.get(auth_messages_url)

        # Should return empty results since anonymous users cannot access user conversations
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_queryset_no_conversation_pk(self) -> None:
        """Test queryset returns empty when no conversation_pk is provided."""
        viewset = AssistantMessageViewSet()
        request = self.factory.get("/api/assistants/messages/")
        viewset.request = request
        viewset.kwargs = {}

        queryset = viewset.get_queryset()
        assert queryset.count() == 0

    @patch("assistants.views.message_views.task_handle_new_assistant_message")
    def test_create_message_authenticated(self, mock_task: Mock) -> None:
        """Test creating a new message triggers AI response."""
        message_data: dict[str, str] = {"content": "Hello AI!"}

        response = self.auth_client.post(self.messages_url, message_data)

        assert response.status_code == status.HTTP_201_CREATED
        data: dict[str, Any] = response.json()
        assert data["content"] == "Hello AI!"

        # The field might be camelCase or snake_case depending on DRF configuration
        message_type = data.get("messageType", data.get("message_type"))
        assert message_type == "user"

        # Verify message was created in database
        message: AssistantMessage = AssistantMessage.objects.get(id=data["id"])
        assert message.conversation == self.conversation
        assert message.message_type == AssistantMessage.MessageType.USER

        # Verify AI task was triggered
        mock_task.assert_called_once_with(user_message_id=message.pk)

    @patch("assistants.views.message_views.task_handle_new_assistant_message")
    def test_create_message_anonymous(self, mock_task: Mock) -> None:
        """Test creating a message in anonymous conversation."""
        anon_conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )
        anon_messages_url = reverse(
            "anonymous-messages-list", kwargs={"conversation_pk": anon_conversation.pk}
        )

        message_data: dict[str, str] = {"content": "Anonymous message"}

        response = self.client.post(anon_messages_url, message_data)

        assert response.status_code == status.HTTP_201_CREATED
        data: dict[str, Any] = response.json()
        assert data["content"] == "Anonymous message"

        # The field might be camelCase or snake_case depending on DRF configuration
        message_type = data.get("messageType", data.get("message_type"))
        assert message_type == "user"

        # Verify message was created in database
        message: AssistantMessage = AssistantMessage.objects.get(id=data["id"])
        assert message.conversation == anon_conversation

        # Verify AI task was triggered
        mock_task.assert_called_once_with(user_message_id=message.pk)

    def test_create_message_unauthenticated_to_authenticated_conversation(self) -> None:
        """Test unauthenticated user cannot create message in authenticated conversation."""
        # Try to access authenticated conversation via anonymous route
        auth_messages_url = reverse(
            "anonymous-messages-list", kwargs={"conversation_pk": self.conversation.pk}
        )

        message_data: dict[str, str] = {"content": "Should fail"}

        response = self.client.post(auth_messages_url, message_data)
        # Should fail because anonymous user cannot find authenticated conversation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_message_authenticated_to_anonymous_conversation(self) -> None:
        """Test authenticated user cannot create message in anonymous conversation."""
        anon_conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )
        anon_messages_url = reverse(
            "anonymous-messages-list", kwargs={"conversation_pk": anon_conversation.pk}
        )

        message_data: dict[str, str] = {"content": "Should fail"}

        response = self.auth_client.post(anon_messages_url, message_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_message_empty_content(self) -> None:
        """Test creating message with empty content fails validation."""
        message_data: dict[str, str] = {"content": ""}

        response = self.auth_client.post(self.messages_url, message_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_message_missing_content(self) -> None:
        """Test creating message without content fails validation."""
        response = self.auth_client.post(self.messages_url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_perform_create_no_conversation_pk(self) -> None:
        """Test perform_create raises ValueError when no conversation_pk is provided."""
        viewset = AssistantMessageViewSet()
        request = self.factory.post("/test/", {"content": "test"})
        viewset.request = request
        viewset.kwargs = {}

        serializer = CreateAssistantMessageSerializer(data={"content": "test"})
        serializer.is_valid()

        with pytest.raises(ValueError, match="conversation_pk is required"):
            viewset.perform_create(serializer)

    @patch("assistants.views.message_views.task_handle_new_assistant_message")
    def test_perform_create_anonymous_user_with_valid_conversation(
        self, mock_task: Mock
    ) -> None:
        """Test perform_create for anonymous user with valid anonymous conversation - covers else branch."""
        anon_conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )

        viewset = AssistantMessageViewSet()
        request = self.factory.post("/test/", {"content": "Anonymous test"})
        request.user = AnonymousUser()
        viewset.request = request
        viewset.kwargs = {"conversation_pk": str(anon_conversation.pk)}

        serializer = CreateAssistantMessageSerializer(
            data={"content": "Anonymous test"}
        )
        serializer.is_valid()

        # This should execute the else branch (anonymous user path)
        viewset.perform_create(serializer)

        # Verify message was created
        message: AssistantMessage = AssistantMessage.objects.get(
            content="Anonymous test"
        )
        assert message.conversation == anon_conversation
        assert message.message_type == AssistantMessage.MessageType.USER

        # Verify task was called
        mock_task.assert_called_once_with(user_message_id=message.pk)

    def test_retrieve_message_authenticated(self) -> None:
        """Test retrieving a specific message."""
        message: AssistantMessage = AssistantMessageFactory.create_user_message(
            conversation=self.conversation, content="Test message"
        )
        detail_url = reverse(
            "conversation-messages-detail",
            kwargs={"conversation_pk": self.conversation.pk, "pk": message.pk},
        )

        response = self.auth_client.get(detail_url)

        assert response.status_code == status.HTTP_200_OK
        data: dict[str, Any] = response.json()
        assert data["id"] == message.pk
        assert data["content"] == "Test message"

    def test_retrieve_message_not_owner(self) -> None:
        """Test user cannot retrieve message from conversation they don't own."""
        other_user: User = UserFactory.create()
        other_conversation: AssistantConversation = AssistantConversationFactory.create(
            user=other_user
        )
        message: AssistantMessage = AssistantMessageFactory.create_user_message(
            conversation=other_conversation
        )

        detail_url = reverse(
            "conversation-messages-detail",
            kwargs={"conversation_pk": other_conversation.pk, "pk": message.pk},
        )

        response = self.auth_client.get(detail_url)
        # Should return 404 since the queryset will be empty (no access to conversation)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_message_not_allowed(self) -> None:
        """Test updating messages is not allowed."""
        message: AssistantMessage = AssistantMessageFactory.create_user_message(
            conversation=self.conversation
        )
        detail_url = reverse(
            "conversation-messages-detail",
            kwargs={"conversation_pk": self.conversation.pk, "pk": message.pk},
        )

        response = self.auth_client.patch(detail_url, {"content": "Updated"})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_message_not_allowed(self) -> None:
        """Test deleting messages is not allowed."""
        message: AssistantMessage = AssistantMessageFactory.create_user_message(
            conversation=self.conversation
        )
        detail_url = reverse(
            "conversation-messages-detail",
            kwargs={"conversation_pk": self.conversation.pk, "pk": message.pk},
        )

        response = self.auth_client.delete(detail_url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
