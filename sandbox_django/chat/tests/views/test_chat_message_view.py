from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from test_utils.auth_api_test_case import AuthAPITestCase

from chat.factories.group_chat import GroupChatFactory
from chat.models import ChatMember, ChatMessage


class ChatMessageViewSetTestCase(AuthAPITestCase):
    """Test case for ChatMessageViewSet REST API."""

    def setUp(self) -> None:
        super().setUp()

        # Create a group chat that the user is a member of
        self.group_chat = GroupChatFactory.create()
        self.chat_member = ChatMember.objects.create(
            user=self.user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
        )

        # Create some sample messages
        self.message1 = ChatMessage.objects.create(
            group_chat=self.group_chat,
            sender=self.chat_member,
            content="Test message 1",
        )

        self.message2 = ChatMessage.objects.create(
            group_chat=self.group_chat,
            sender=self.chat_member,
            content="Test message 2",
        )

        # URL for listing messages
        self.list_url = reverse(
            "chat-messages-list", kwargs={"group_chat_pk": self.group_chat.pk}
        )

    def test_list_messages(self) -> None:
        """Test listing messages for a group chat."""
        # Make the request
        response = self.auth_client.get(self.list_url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

        # Messages are returned newest first due to ordering
        assert response.data["results"][0]["content"] == "Test message 2"
        assert response.data["results"][1]["content"] == "Test message 1"

    def test_create_message(self) -> None:
        """Test creating a new message in a group chat."""
        # Message data
        message_data = {"content": "New test message"}

        # Make the request
        response = self.auth_client.post(self.list_url, message_data)

        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == "New test message"
        assert response.data["is_mine"] is True

        # Verify the message was created in the database
        messages = ChatMessage.objects.filter(group_chat=self.group_chat)
        assert messages.count() == 3
        latest_message = messages.latest("id")
        assert latest_message.content == "New test message"

    def test_retrieve_message(self) -> None:
        """Test retrieving a single message."""
        # URL for retrieving a single message
        detail_url = reverse(
            "chat-messages-detail",
            kwargs={"group_chat_pk": self.group_chat.pk, "pk": self.message1.pk},
        )

        # Make the request
        response = self.auth_client.get(detail_url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.data["content"] == "Test message 1"
        assert "sender" in response.data
        assert "is_mine" in response.data
        assert "formatted_time" in response.data

    def test_pagination(self) -> None:
        """Test that messages are paginated correctly."""
        # Create more messages to trigger pagination
        for i in range(25):  # Default page size is 20
            ChatMessage.objects.create(
                group_chat=self.group_chat,
                sender=self.chat_member,
                content=f"Pagination test message {i}",
            )

        # Make the request
        response = self.auth_client.get(self.list_url)

        # Verify pagination
        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert "results" in response.data

        # Default page size is 20
        assert len(response.data["results"]) == 20

        # Get next page
        next_page_url = response.data["next"]
        response = self.auth_client.get(next_page_url)

        # Verify second page
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 7  # 27 total messages, 7 on second page

    def test_non_member_cannot_access_messages(self) -> None:
        """Test that a non-member cannot access messages in a group chat."""
        # Create a new user who is not a member of the group chat
        other_user = UserFactory.create()
        other_client = self.get_client_for_user(other_user)

        # Make the request
        response = other_client.get(self.list_url)

        # Verify the user cannot access the messages
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_message_sender_info(self) -> None:
        """Test that messages include sender information."""
        # Make the request
        response = self.auth_client.get(self.list_url)

        # Verify response includes sender info
        assert response.status_code == status.HTTP_200_OK

        # Check sender info in the first message
        message = response.data["results"][0]
        assert "sender" in message
        assert message["sender"]["user"] == self.user.email

    def test_is_mine_flag(self) -> None:
        """Test that messages have correct is_mine flag."""
        # Create a message from another user
        other_user = UserFactory.create(email="other@mail.com")
        other_member = ChatMember.objects.create(
            user=other_user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
        )

        ChatMessage.objects.create(
            group_chat=self.group_chat,
            sender=other_member,
            content="Message from other user",
        )

        # Make the request
        response = self.auth_client.get(self.list_url)

        # Verify response
        assert response.status_code == status.HTTP_200_OK

        # Find messages by content
        other_user_message = next(
            (
                m
                for m in response.data["results"]
                if m["content"] == "Message from other user"
            ),
            None,
        )
        my_message = next(
            (m for m in response.data["results"] if m["content"] == "Test message 2"),
            None,
        )

        # Check is_mine flag
        assert other_user_message is not None
        assert my_message is not None
        assert other_user_message["is_mine"] is False
        assert my_message["is_mine"] is True

    def test_nonexistent_group_chat(self) -> None:
        """Test accessing messages for a nonexistent group chat."""
        # URL for a nonexistent group chat
        nonexistent_url = reverse("chat-messages-list", kwargs={"group_chat_pk": 99999})

        # Make the request
        response = self.auth_client.get(nonexistent_url)

        # Verify response
        assert response.status_code == status.HTTP_403_FORBIDDEN
