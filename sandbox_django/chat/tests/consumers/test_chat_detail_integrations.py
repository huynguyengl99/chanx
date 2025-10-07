from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from asgiref.sync import sync_to_async
from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.auth_api_test_case import AuthAPITestCase
from test_utils.testing import WebsocketTestCase

from chat.consumers.chat_detail import ChatDetailConsumer
from chat.factories.chat_member import ChatMemberFactory
from chat.models import ChatMember, ChatMessage, GroupChat


class TestChatDetailConsumerIntegration(WebsocketTestCase):
    """Integration tests for ChatDetailConsumer - tests full API → WebSocket flow"""

    consumer = ChatDetailConsumer

    def setUp(self) -> None:
        super().setUp()
        # Create a group chat for testing
        self.group_chat = GroupChat.objects.create(title="Test Group Chat")

        # Add the authenticated user as an ADMIN member so they can manage members
        ChatMemberFactory.create_admin(user=self.user, group_chat=self.group_chat)

        # Set up authenticated API client
        self.api_client = AuthAPITestCase.get_client_for_user(self.user)

        self.ws_path = f"/ws/chat/{self.group_chat.pk}/"

    async def test_member_addition_via_api(self) -> None:
        """Test full member addition flow: API call → Task → WebSocket notification"""
        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create a new user to add to the group
        new_user = await UserFactory.acreate(email="newuser@test.com")

        # Prepare member addition data
        member_data = {
            "email": new_user.email,
            "role": str(ChatMember.ChatMemberRole.MEMBER),
        }

        # Add member via REST API using clean sync_to_async pattern
        response = await sync_to_async(self.api_client.post)(
            reverse("group_members", kwargs={"pk": self.group_chat.pk}),
            member_data,
        )

        # Verify the API call was successful (redirect = 302)
        assert response.status_code == status.HTTP_302_FOUND

        # Verify the member was actually added to the database
        member_exists = await sync_to_async(
            ChatMember.objects.filter(user=new_user, group_chat=self.group_chat).exists
        )()
        assert member_exists

        # Receive WebSocket notification about the new member
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Should receive a member_added message
        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "member_added"
        # The payload should contain member information
        payload = message.payload
        assert payload["user"] == new_user.email

    async def test_member_addition_as_admin_role_via_api(self) -> None:
        """Test adding a member with admin role via API"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        new_user = await UserFactory.acreate(email="adminuser@test.com")

        member_data = {
            "email": new_user.email,
            "role": str(ChatMember.ChatMemberRole.ADMIN),
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("group_members", kwargs={"pk": self.group_chat.pk}),
            member_data,
        )

        assert response.status_code == status.HTTP_302_FOUND

        # Verify the member was added with admin role
        new_member = await sync_to_async(ChatMember.objects.get)(
            user=new_user, group_chat=self.group_chat
        )
        assert new_member.chat_role == ChatMember.ChatMemberRole.ADMIN

        # Verify WebSocket notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )
        assert len(all_messages) == 1
        assert all_messages[0].action == "member_added"

    async def test_member_removal_other_user_via_api(self) -> None:
        """Test member removal flow for other users: API call → Task → WebSocket notification"""
        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create and add a member to remove
        user_to_remove = await UserFactory.acreate(email="toremove@test.com")
        member_to_remove = await ChatMemberFactory.acreate(
            user=user_to_remove, group_chat=self.group_chat
        )

        # Remove member via REST API
        response = await sync_to_async(self.api_client.get)(
            reverse(
                "remove_member",
                kwargs={
                    "pk": self.group_chat.pk,
                    "member_id": member_to_remove.pk,
                },
            ),
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_302_FOUND

        # Verify the member was removed from the database
        member_exists = await sync_to_async(
            ChatMember.objects.filter(pk=member_to_remove.pk).exists
        )()
        assert not member_exists

        # Receive WebSocket notification about member removal
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Should receive a member_removed message
        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "member_removed"
        assert hasattr(message, "payload")
        payload = message.payload
        assert payload.user_pk == user_to_remove.pk
        assert payload.email == user_to_remove.email

    async def test_self_removal_via_api(self) -> None:
        """Test that current user gets disconnected when removed via API"""
        # Create a second user who will be the owner and remove the first user
        owner_user = await UserFactory.acreate(email="owner@test.com")
        await ChatMemberFactory.acreate_owner(
            user=owner_user, group_chat=self.group_chat
        )

        # Connect the user who will be removed
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Get the current user's member object
        current_user_member = await ChatMember.objects.aget(
            user=self.user, group_chat=self.group_chat
        )

        # Create API client authenticated as the owner
        owner_api_client = await AuthAPITestCase.aget_client_for_user(owner_user)

        # Remove the current user via REST API
        response = await sync_to_async(owner_api_client.get)(
            reverse(
                "remove_member",
                kwargs={
                    "pk": self.group_chat.pk,
                    "member_id": current_user_member.pk,
                },
            ),
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_302_FOUND

        # Receive WebSocket notification - should be user_removed_from_group
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "user_removed_from_group"
        assert hasattr(message, "payload")
        payload = message.payload
        assert payload.redirect == "/chat/"
        assert "removed" in payload.message

    async def test_chat_message_creation_via_api(self) -> None:
        """Test chat message creation flow: API call → Task → WebSocket notification"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create a new message via REST API
        message_data = {"content": "Hello everyone via API!"}

        response = await sync_to_async(self.api_client.post)(
            reverse("chat-messages-list", kwargs={"group_chat_pk": self.group_chat.pk}),
            message_data,
            format="json",
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_201_CREATED

        # Verify the message was created in the database
        message_exists = await sync_to_async(
            ChatMessage.objects.filter(
                group_chat=self.group_chat, content="Hello everyone via API!"
            ).exists
        )()
        assert message_exists

        # Receive WebSocket notification about the new message
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Should receive a member_message with the new message
        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "member_message"
        assert message.payload["is_mine"] is True  # Message from current user
        assert message.payload["content"] == "Hello everyone via API!"

    async def test_chat_message_from_other_user_via_api(self) -> None:
        """Test receiving messages from other users via API"""
        # Create another user and add them to the group
        other_user = await UserFactory.acreate(email="other@test.com")
        await ChatMemberFactory.acreate(user=other_user, group_chat=self.group_chat)

        # Connect current user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create API client for the other user
        other_api_client = await AuthAPITestCase.aget_client_for_user(other_user)

        # Other user sends a message
        message_data = {"content": "Hello from another user!"}

        response = await sync_to_async(other_api_client.post)(
            reverse("chat-messages-list", kwargs={"group_chat_pk": self.group_chat.pk}),
            message_data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Current user should receive WebSocket notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "member_message"
        assert message.payload["is_mine"] is False  # Message from other user
        assert message.payload["content"] == "Hello from another user!"

    async def test_api_error_handling_member_addition(self) -> None:
        """Test that API errors don't break WebSocket connection"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Try to add a non-existent user
        member_data = {
            "email": "nonexistent@test.com",
            "role": str(ChatMember.ChatMemberRole.MEMBER),
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("group_members", kwargs={"pk": self.group_chat.pk}),
            member_data,
        )

        # API should handle the error gracefully (redirect with error message)
        assert response.status_code == status.HTTP_302_FOUND

        # No WebSocket message should be sent for failed addition
        assert await self.auth_communicator.receive_nothing()

        # Connection should still be active
        await self.auth_communicator.send_message(PingMessage())
        ping_response = await self.auth_communicator.receive_all_messages()
        assert ping_response == [PongMessage()]

    async def test_unauthorized_member_management_via_api(self) -> None:
        """Test that unauthorized users cannot manage members via API"""

        # Connect regular user to WebSocket
        regular_user, regular_user_headers = await self.acreate_user_and_ws_headers()
        await ChatMemberFactory.acreate(user=regular_user, group_chat=self.group_chat)
        regular_communicator = self.create_communicator(headers=regular_user_headers)
        await regular_communicator.connect()
        await regular_communicator.assert_authenticated_status_ok()

        # Try to add a member as regular user
        regular_api_client = await AuthAPITestCase.aget_client_for_user(regular_user)

        new_user = await UserFactory.acreate(email="unauthorized@test.com")
        member_data = {
            "email": new_user.email,
            "role": str(ChatMember.ChatMemberRole.MEMBER),
        }

        response = await sync_to_async(regular_api_client.post)(
            reverse("group_members", kwargs={"pk": self.group_chat.pk}),
            member_data,
        )

        # Should be redirected with error message (new behavior with AllowAny permissions)
        assert response.status_code == status.HTTP_302_FOUND

        # No member should be added
        member_exists = await sync_to_async(
            ChatMember.objects.filter(user=new_user, group_chat=self.group_chat).exists
        )()
        assert not member_exists

        # No WebSocket notification should be sent
        assert await regular_communicator.receive_nothing()
