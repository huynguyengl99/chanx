from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from asgiref.sync import sync_to_async
from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.auth_api_test_case import AuthAPITestCase
from test_utils.testing import WebsocketTestCase

from chat.consumers.group import GroupChatConsumer
from chat.factories.chat_member import ChatMemberFactory
from chat.factories.group_chat import GroupChatFactory
from chat.models import ChatMember, ChatMessage, GroupChat


class TestGroupChatConsumerIntegration(WebsocketTestCase):
    """Integration tests for GroupChatConsumer - tests full API → WebSocket flow"""

    consumer = GroupChatConsumer

    def setUp(self) -> None:
        super().setUp()
        self.ws_path = "/ws/chat/group/"

        # Set up authenticated API client
        self.api_client = AuthAPITestCase.get_client_for_user(self.user)

    async def test_group_chat_creation_via_api(self) -> None:
        """Test full group chat creation flow: API call → Task → WebSocket notification"""
        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create a new group chat via REST API
        group_data = {
            "title": "API Created Group",
            "description": "Created via API test",
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("groupchat-list"), group_data, format="json"
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_201_CREATED

        # Verify the group chat was created in the database
        group_chat = await sync_to_async(GroupChat.objects.get)(
            title="API Created Group"
        )
        assert group_chat.description == "Created via API test"

        # Verify the user was added as owner
        member = await sync_to_async(ChatMember.objects.get)(
            user=self.user, group_chat=group_chat
        )
        assert member.chat_role == ChatMember.ChatMemberRole.OWNER

        # Receive WebSocket notifications
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Should receive added_to_group
        assert len(all_messages) == 1

        # Check added_to_group message
        added_message = next(
            msg for msg in all_messages if msg.action == "added_to_group"
        )
        assert added_message.payload["id"] == group_chat.pk
        assert added_message.payload["title"] == "API Created Group"

    async def test_member_addition_notification_via_api(self) -> None:
        """Test receiving notifications when added to a group via API"""
        # Create another user who will create the group and add our user
        admin_user = await UserFactory.acreate(email="admin@test.com")
        admin_api_client = await AuthAPITestCase.aget_client_for_user(admin_user)

        # Create a group chat with admin as owner
        group_chat = await GroupChatFactory.acreate(title="Admin's Group")
        await ChatMemberFactory.acreate_owner(user=admin_user, group_chat=group_chat)

        # Connect our user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Admin adds our user to the group via API
        member_data = {
            "email": self.user.email,
            "role": str(ChatMember.ChatMemberRole.MEMBER),
        }

        response = await sync_to_async(admin_api_client.post)(
            reverse("group_members", kwargs={"pk": group_chat.pk}),
            member_data,
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_302_FOUND

        # Verify our user was added to the group
        member = await sync_to_async(ChatMember.objects.get)(
            user=self.user, group_chat=group_chat
        )
        assert member.chat_role == ChatMember.ChatMemberRole.MEMBER

        # Should receive added_to_group notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]
        assert message.action == "added_to_group"
        assert message.payload["id"] == group_chat.pk
        assert message.payload["title"] == "Admin's Group"

    async def test_member_removal_notification_via_api(self) -> None:
        """Test receiving notifications when removed from a group via API"""
        # Create another user who will be the admin
        admin_user = await UserFactory.acreate(email="admin@test.com")
        admin_api_client = await AuthAPITestCase.aget_client_for_user(admin_user)

        # Create a group chat with both users
        group_chat = await GroupChatFactory.acreate(title="Removal Test Group")
        await ChatMemberFactory.acreate_owner(user=admin_user, group_chat=group_chat)
        user_member = await ChatMemberFactory.acreate(
            user=self.user, group_chat=group_chat
        )

        # Connect our user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Admin removes our user from the group via API
        response = await sync_to_async(admin_api_client.get)(
            reverse(
                "remove_member",
                kwargs={"pk": group_chat.pk, "member_id": user_member.pk},
            ),
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_302_FOUND

        # Verify our user was removed from the group
        member_exists = await sync_to_async(
            ChatMember.objects.filter(user=self.user, group_chat=group_chat).exists
        )()
        assert not member_exists

        # Should receive removed_from_group notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]
        assert message.action == "removed_from_group"
        assert message.payload.group_pk == group_chat.pk
        assert message.payload.group_title == "Removal Test Group"

    async def test_group_chat_update_from_message_activity(self) -> None:
        """Test receiving update notifications when messages are posted to groups"""
        # Create a group chat where our user is a member
        group_chat = await GroupChatFactory.acreate(title="Message Activity Group")
        await ChatMemberFactory.acreate(user=self.user, group_chat=group_chat)

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Post a message to the group chat via API (triggers update)
        message_data = {"content": "This message should trigger an update"}

        response = await sync_to_async(self.api_client.post)(
            reverse("chat-messages-list", kwargs={"group_chat_pk": group_chat.pk}),
            message_data,
            format="json",
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_201_CREATED

        # Verify the message was created
        message_exists = await sync_to_async(
            ChatMessage.objects.filter(
                group_chat=group_chat, content="This message should trigger an update"
            ).exists
        )()
        assert message_exists

        # Should receive group_chat_updated notification (due to updated timestamp)
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Find the group_chat_updated message (there might be other messages too)
        update_messages = [
            msg for msg in all_messages if msg.action == "group_chat_updated"
        ]
        assert len(update_messages) >= 1

        update_message = update_messages[0]
        assert update_message.payload.group_pk == group_chat.pk

    async def test_multiple_users_receiving_updates(self) -> None:
        """Test that multiple users receive the same update notifications"""
        other_user, other_user_headers = await self.acreate_user_and_ws_headers()

        # Create a group chat with the owner user
        owner_user = await UserFactory.acreate(email="owner@test.com")
        group_chat = await GroupChatFactory.acreate(title="Multi-User Group")
        await ChatMemberFactory.acreate_owner(user=owner_user, group_chat=group_chat)

        # Add both users to the group
        await ChatMemberFactory.acreate(user=self.user, group_chat=group_chat)
        await ChatMemberFactory.acreate(user=other_user, group_chat=group_chat)

        # Connect first user to Websocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Connect second user to WebSocket

        other_communicator = self.create_communicator(headers=other_user_headers)
        await other_communicator.connect()
        await other_communicator.assert_authenticated_status_ok()

        # Owner updates the group chat
        owner_api_client = await AuthAPITestCase.aget_client_for_user(owner_user)
        update_data = {
            "title": "Updated Multi-User Group",
            "description": "Updated by owner",
        }

        response = await sync_to_async(owner_api_client.put)(
            reverse("groupchat-detail", kwargs={"pk": group_chat.pk}),
            update_data,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Both users should receive the update notification
        user1_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )
        user2_messages = await other_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Both should have received group_chat_updated messages
        user1_updates = [
            msg for msg in user1_messages if msg.action == "group_chat_updated"
        ]
        user2_updates = [
            msg for msg in user2_messages if msg.action == "group_chat_updated"
        ]

        assert len(user1_updates) >= 1
        assert len(user2_updates) >= 1

        # Both should have the same group_pk in the payload
        assert user1_updates[0].payload.group_pk == group_chat.pk
        assert user2_updates[0].payload.group_pk == group_chat.pk

    async def test_user_not_in_group_no_update_notification(self) -> None:
        """Test that users not in a group don't receive update notifications for that group"""
        # Create another user who will create and update a group
        other_user = await UserFactory.acreate(email="other@test.com")
        other_api_client = await AuthAPITestCase.aget_client_for_user(other_user)

        # Create a group chat where our user is NOT a member
        group_chat = await GroupChatFactory.acreate(title="Private Group")
        await ChatMemberFactory.acreate_owner(user=other_user, group_chat=group_chat)

        # Connect our user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Other user updates their group
        update_data = {"title": "Updated Private Group", "description": "Updated"}

        response = await sync_to_async(other_api_client.put)(
            reverse("groupchat-detail", kwargs={"pk": group_chat.pk}),
            update_data,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Our user should NOT receive any notifications about this group
        assert await self.auth_communicator.receive_nothing()

        # Verify connection is still active
        await self.auth_communicator.send_message(PingMessage())
        ping_response = await self.auth_communicator.receive_all_messages()
        assert ping_response == [PongMessage()]

    async def test_api_error_handling_no_false_notifications(self) -> None:
        """Test that API errors don't generate false WebSocket notifications"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Try to create a group chat with invalid data
        invalid_data = {"title": ""}  # Empty title should fail validation

        response = await sync_to_async(self.api_client.post)(
            reverse("groupchat-list"), invalid_data, format="json"
        )

        # API should reject the request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Should not receive any WebSocket notifications for failed creation
        assert await self.auth_communicator.receive_nothing()

        # Connection should still be active
        await self.auth_communicator.send_message(PingMessage())
        ping_response = await self.auth_communicator.receive_all_messages()
        assert ping_response == [PongMessage()]

    async def test_unauthorized_group_operations_no_notifications(self) -> None:
        """Test that unauthorized operations don't generate notifications"""
        # Create another user's group
        other_user = await UserFactory.acreate(email="other@test.com")
        group_chat = await GroupChatFactory.acreate(title="Other's Group")
        await ChatMemberFactory.acreate_owner(user=other_user, group_chat=group_chat)

        # Connect our user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Try to update the other user's group (should fail)
        update_data = {"title": "Hacked Group", "description": "Unauthorized update"}

        response = await sync_to_async(self.api_client.put)(
            reverse("groupchat-detail", kwargs={"pk": group_chat.pk}),
            update_data,
            format="json",
        )

        # Should be forbidden or not found (depending on permission implementation)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

        # Should not receive any notifications
        assert await self.auth_communicator.receive_nothing()

        # Verify the group was not actually updated
        await sync_to_async(group_chat.refresh_from_db)()
        assert group_chat.title == "Other's Group"  # Unchanged
