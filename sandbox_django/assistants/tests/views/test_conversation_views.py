from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from accounts.models import User
from test_utils.auth_api_test_case import AuthAPITestCase

from assistants.factories import AssistantConversationFactory
from assistants.models import AssistantConversation


class AssistantConversationViewSetTestCase(AuthAPITestCase):
    """Test cases for AssistantConversationViewSet."""

    def setUp(self) -> None:
        super().setUp()
        self.list_url = reverse("assistant-conversations-list")

    def test_list_conversations_authenticated(self) -> None:
        """Test listing conversations for authenticated user."""
        # Create conversations for the user
        conv1: AssistantConversation = AssistantConversationFactory.create(
            user=self.user, title="First Conv"
        )
        conv2: AssistantConversation = AssistantConversationFactory.create(
            user=self.user, title="Second Conv"
        )

        # Create conversation for another user (should not be included)
        other_user: User = UserFactory.create()
        AssistantConversationFactory.create(user=other_user, title="Other User Conv")

        response = self.auth_client.get(self.list_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 2

        # Check conversations are ordered by updatedAt desc
        titles = [conv["title"] for conv in data["results"]]
        assert conv2.title in titles
        assert conv1.title in titles

    def test_list_conversations_unauthenticated(self) -> None:
        """Test listing conversations requires authentication."""
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_conversation_authenticated(self) -> None:
        """Test creating a new conversation."""
        response = self.auth_client.post(self.list_url, {})

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["title"] == ""

        # Verify conversation was created in database
        conversation: AssistantConversation = AssistantConversation.objects.get(
            id=data["id"]
        )
        assert conversation.user == self.user

    def test_create_conversation_unauthenticated(self) -> None:
        """Test creating conversation requires authentication."""
        response = self.client.post(self.list_url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_conversation_authenticated(self) -> None:
        """Test retrieving a specific conversation."""
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=self.user, title="Test Conversation"
        )
        detail_url = reverse(
            "assistant-conversations-detail", kwargs={"pk": conversation.pk}
        )

        response = self.auth_client.get(detail_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(conversation.id)
        assert data["title"] == "Test Conversation"

    def test_retrieve_conversation_not_owner(self) -> None:
        """Test user cannot retrieve conversation they don't own."""
        other_user: User = UserFactory.create()
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=other_user
        )
        detail_url = reverse(
            "assistant-conversations-detail", kwargs={"pk": conversation.pk}
        )

        response = self.auth_client.get(detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_conversation_authenticated(self) -> None:
        """Test updating a conversation."""
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=self.user
        )
        detail_url = reverse(
            "assistant-conversations-detail", kwargs={"pk": conversation.pk}
        )

        response = self.auth_client.patch(detail_url, {"title": "Updated Title"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"

        conversation.refresh_from_db()
        assert conversation.title == "Updated Title"

    def test_update_conversation_not_owner(self) -> None:
        """Test user cannot update conversation they don't own."""
        other_user: User = UserFactory.create()
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=other_user
        )
        detail_url = reverse(
            "assistant-conversations-detail", kwargs={"pk": conversation.pk}
        )

        response = self.auth_client.patch(detail_url, {"title": "Updated Title"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_conversation_authenticated(self) -> None:
        """Test deleting a conversation."""
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=self.user
        )
        detail_url = reverse(
            "assistant-conversations-detail", kwargs={"pk": conversation.pk}
        )

        response = self.auth_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not AssistantConversation.objects.filter(id=conversation.id).exists()

    def test_delete_conversation_not_owner(self) -> None:
        """Test user cannot delete conversation they don't own."""
        other_user: User = UserFactory.create()
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=other_user
        )
        detail_url = reverse(
            "assistant-conversations-detail", kwargs={"pk": conversation.pk}
        )

        response = self.auth_client.delete(detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify conversation still exists
        assert AssistantConversation.objects.filter(id=conversation.id).exists()
