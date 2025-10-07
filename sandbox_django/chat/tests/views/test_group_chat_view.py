from django.urls import reverse
from rest_framework import status

from test_utils.auth_api_test_case import AuthAPITestCase

from chat.factories.chat_member import ChatMemberFactory
from chat.factories.group_chat import GroupChatFactory
from chat.models import GroupChat


class GroupChatViewSetTestCase(AuthAPITestCase):
    """Test case for GroupChatViewSet REST API."""

    def setUp(self) -> None:
        super().setUp()
        self.list_url = reverse("groupchat-list")

    def test_list_authenticated_user_chats(self) -> None:
        """Test that an authenticated user can list their group chats."""
        # Create some group chats for the authenticated user
        group_chat1 = GroupChatFactory.create(title="Chat 1")
        group_chat2 = GroupChatFactory.create(title="Chat 2")

        # Add the user to these group chats
        ChatMemberFactory.create_owner(user=self.user, group_chat=group_chat1)
        ChatMemberFactory.create(user=self.user, group_chat=group_chat2)

        # Create a group chat that the user is not a member of
        GroupChatFactory.create(title="Not My Chat")

        # Make the request
        response = self.auth_client.get(self.list_url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Extract chat titles for easier comparison
        response_titles = [chat["title"] for chat in response.data["results"]]

        # Verify the user can only see their chats
        assert "Chat 1" in response_titles
        assert "Chat 2" in response_titles
        assert "Not My Chat" not in response_titles
        assert len(response.data["results"]) == 2

    def test_create_group_chat(self) -> None:
        """Test creating a new group chat."""
        # Chat data
        chat_data = {"title": "New Test Chat", "description": "This is a test chat"}

        # Make the request
        response = self.auth_client.post(self.list_url, chat_data)

        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Test Chat"
        assert response.data["description"] == "This is a test chat"

        # Verify the chat was created in the database
        chat_id = response.data["id"]
        chat = GroupChat.objects.get(id=chat_id)
        assert chat.title == "New Test Chat"

        # Verify the user was added as an owner
        member = chat.members.get(user=self.user)
        assert member.chat_role == member.ChatMemberRole.OWNER

    def test_update_group_chat(self) -> None:
        """Test updating a group chat."""
        # Create a group chat owned by the authenticated user
        group_chat = GroupChatFactory.create(title="Original Title")
        ChatMemberFactory.create_owner(user=self.user, group_chat=group_chat)

        # URL for the detail view
        detail_url = reverse("groupchat-detail", kwargs={"pk": group_chat.pk})

        # Updated data
        updated_data = {"title": "Updated Title", "description": "Updated description"}

        # Make the request
        response = self.auth_client.put(detail_url, updated_data)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Updated Title"

        # Verify the changes in the database
        group_chat.refresh_from_db()
        assert group_chat.title == "Updated Title"
        assert group_chat.description == "Updated description"

    def test_partial_update_group_chat(self) -> None:
        """Test partial update (PATCH) of a group chat."""
        # Create a group chat owned by the authenticated user
        group_chat = GroupChatFactory.create(
            title="Original Title", description="Original description"
        )
        ChatMemberFactory.create_owner(user=self.user, group_chat=group_chat)

        # URL for the detail view
        detail_url = reverse("groupchat-detail", kwargs={"pk": group_chat.pk})

        # Partial update data (only updating title)
        patch_data = {"title": "Patched Title"}

        # Make the request
        response = self.auth_client.patch(detail_url, patch_data)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Patched Title"

        # Verify the changes in the database
        group_chat.refresh_from_db()
        assert group_chat.title == "Patched Title"
        assert (
            group_chat.description == "Original description"
        )  # Should remain unchanged

    def test_delete_group_chat(self) -> None:
        """Test deleting a group chat."""
        # Create a group chat owned by the authenticated user
        group_chat = GroupChatFactory.create()
        ChatMemberFactory.create_owner(user=self.user, group_chat=group_chat)

        # URL for the detail view
        detail_url = reverse("groupchat-detail", kwargs={"pk": group_chat.pk})

        # Make the request
        response = self.auth_client.delete(detail_url)

        # Verify response
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify the chat was deleted
        assert not GroupChat.objects.filter(pk=group_chat.pk).exists()

    def test_non_member_cannot_access_chat(self) -> None:
        """Test that a non-member cannot access a group chat."""
        # Create a group chat that the user is not a member of
        group_chat = GroupChatFactory.create()

        # URL for the detail view
        detail_url = reverse("groupchat-detail", kwargs={"pk": group_chat.pk})

        # Make the request
        response = self.auth_client.get(detail_url)

        # Verify the user cannot access the chat
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_owner_cannot_update_chat(self) -> None:
        """Test that a non-owner cannot update a group chat."""
        # Create a group chat where the authenticated user is only a member (not owner)
        group_chat = GroupChatFactory.create()
        ChatMemberFactory.create(user=self.user, group_chat=group_chat)

        # URL for the detail view
        detail_url = reverse("groupchat-detail", kwargs={"pk": group_chat.pk})

        # Updated data
        updated_data = {"title": "Unauthorized Update"}

        # Make the request
        response = self.auth_client.put(detail_url, updated_data)

        # Verify the user cannot update the chat
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_owner_cannot_delete_chat(self) -> None:
        """Test that a non-owner cannot delete a group chat."""
        # Create a group chat where the authenticated user is only a member (not owner)
        group_chat = GroupChatFactory.create()
        ChatMemberFactory.create(user=self.user, group_chat=group_chat)

        # URL for the detail view
        detail_url = reverse("groupchat-detail", kwargs={"pk": group_chat.pk})

        # Make the request
        response = self.auth_client.delete(detail_url)

        # Verify the user cannot delete the chat
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify the chat still exists
        assert GroupChat.objects.filter(pk=group_chat.pk).exists()

    def test_unauthenticated_user_cannot_list_chats(self) -> None:
        """Test that an unauthenticated user cannot list group chats."""
        # Make the request with unauthenticated client
        response = self.client.get(self.list_url)

        # Verify the response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
