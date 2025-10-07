from unittest.mock import Mock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from assistants.models import AssistantConversation


class CreateAnonymousConversationTestCase(APITestCase):
    """Test cases for create_anonymous_conversation view."""

    def setUp(self) -> None:
        self.url = reverse("create-anonymous-conversation")

    def test_create_anonymous_conversation_success(self) -> None:
        """Test successfully creating an anonymous conversation."""
        response = self.client.post(self.url, {})

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "id" in data
        assert data["title"] == "New Anonymous Chat"
        assert data["isAnonymous"] is True
        assert "createdAt" in data

        # Verify conversation was created in database
        conversation: AssistantConversation = AssistantConversation.objects.get(
            id=data["id"]
        )
        assert conversation.user is None  # Anonymous conversation
        assert conversation.title == ""

    def test_create_anonymous_conversation_multiple(self) -> None:
        """Test creating multiple anonymous conversations."""
        response1 = self.client.post(self.url, {})
        response2 = self.client.post(self.url, {})

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED

        data1 = response1.json()
        data2 = response2.json()

        # Should create different conversations
        assert data1["id"] != data2["id"]

        # Verify both exist in database
        assert AssistantConversation.objects.filter(id=data1["id"]).exists()
        assert AssistantConversation.objects.filter(id=data2["id"]).exists()

    def test_create_anonymous_conversation_get_method_not_allowed(self) -> None:
        """Test GET method is not allowed."""
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_create_anonymous_conversation_put_method_not_allowed(self) -> None:
        """Test PUT method is not allowed."""
        response = self.client.put(self.url, {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_create_anonymous_conversation_delete_method_not_allowed(self) -> None:
        """Test DELETE method is not allowed."""
        response = self.client.delete(self.url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @patch("assistants.models.AssistantConversation.objects.create")
    def test_create_anonymous_conversation_exception_handling(
        self, mock_create: Mock
    ) -> None:
        """Test exception handling when conversation creation fails."""
        # Mock an exception during conversation creation
        mock_create.side_effect = Exception("Database error")

        response = self.client.post(self.url, {})

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data
        assert "Database error" in data["error"]
