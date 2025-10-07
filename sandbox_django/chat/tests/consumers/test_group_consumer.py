import sys
from typing import cast

from django.conf import settings
from rest_framework import status

from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.testing import WebsocketTestCase

from chat.consumers.group import GroupChatConsumer
from chat.messages.group import (
    AddedToGroupMessage,
    GroupChatUpdatePayload,
    GroupRemovePayload,
    NotifyAddedToGroupEvent,
    NotifyGroupChatUpdateEvent,
    NotifyRemovedFromGroupEvent,
    RemovedFromGroupMessage,
)

if sys.version_info < (3, 11):  # pragma: no cover
    pass


class TestGroupChatConsumer(WebsocketTestCase):
    """Unit tests for GroupChatConsumer - focuses on consumer event handling logic"""

    consumer = GroupChatConsumer

    def setUp(self) -> None:
        super().setUp()
        self.ws_path = "/ws/chat/group/"

    async def test_connect_successfully_and_ping(self) -> None:
        """Test basic connection and ping/pong functionality"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        await self.auth_communicator.send_message(PingMessage())

        all_messages = await self.auth_communicator.receive_all_messages()
        assert all_messages == [PongMessage()]

    async def test_unauthenticated_user_connection(self) -> None:
        """Test that unauthenticated users cannot connect"""
        # Create unauthenticated headers (no cookies)
        unauthenticated_communicator = self.create_communicator(
            headers=[
                (b"origin", settings.SERVER_URL.encode()),
            ]
        )

        # Try to connect - this should fail
        await unauthenticated_communicator.connect()

        # Check authentication response
        auth = await unauthenticated_communicator.wait_for_auth(max_auth_time=1000)
        assert auth
        assert auth.payload.status_code == status.HTTP_401_UNAUTHORIZED

        # Connection should be closed
        await unauthenticated_communicator.assert_closed()

    async def test_notify_added_to_group_event(self) -> None:
        """Test consumer handles group addition notifications correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test group chat data
        test_group_payload = {
            "id": 123,
            "title": "New Test Group",
            "description": "A test group chat",
        }

        # Send added to group event to user's personal channel
        user_group_name = f"user_{self.user.pk}_groups"
        await GroupChatConsumer.broadcast_event(
            NotifyAddedToGroupEvent(payload=test_group_payload),
            [user_group_name],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(AddedToGroupMessage, all_messages[0])
        assert message.action == "added_to_group"
        assert message.payload == test_group_payload

    async def test_notify_removed_from_group_event(self) -> None:
        """Test consumer handles group removal notifications correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test removal payload using proper model
        removal_payload = GroupRemovePayload(group_pk=456, group_title="Removed Group")

        # Send removed from group event to user's personal channel
        user_group_name = f"user_{self.user.pk}_groups"
        await GroupChatConsumer.broadcast_event(
            NotifyRemovedFromGroupEvent(payload=removal_payload),
            [user_group_name],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(RemovedFromGroupMessage, all_messages[0])
        assert message.action == "removed_from_group"
        assert message.payload.group_pk == 456
        assert message.payload.group_title == "Removed Group"

    async def test_notify_group_chat_update_event(self) -> None:
        """Test consumer handles group chat update notifications correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test update payload using proper model
        update_payload = GroupChatUpdatePayload(
            group_pk=789, updated_at="2023-01-01T12:00:00Z"
        )

        # Send to a group update channel (user needs to be subscribed to receive this)
        group_update_channel = "group_chat_789_updates"
        await GroupChatConsumer.broadcast_event(
            NotifyGroupChatUpdateEvent(payload=update_payload),
            [group_update_channel],
        )

        # Should not receive anything since user is not subscribed to group 789
        assert await self.auth_communicator.receive_nothing(timeout=1)

    async def test_events_to_wrong_user_group_not_received(self) -> None:
        """Test that events sent to other users' groups are not received"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send event to a different user's group
        other_user_group_name = f"user_{self.user.pk + 999}_groups"
        test_group_payload = {
            "id": 999,
            "title": "Private Group",
            "description": "Not for this user",
        }

        await GroupChatConsumer.broadcast_event(
            NotifyAddedToGroupEvent(payload=test_group_payload),
            [other_user_group_name],
        )

        # Should not receive any messages
        assert await self.auth_communicator.receive_nothing()

    async def test_connection_stability_after_events(self) -> None:
        """Test that connection remains stable after processing events"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send an event
        user_group_name = f"user_{self.user.pk}_groups"
        test_payload = {"id": 123, "title": "Stability Test", "description": "Test"}

        await GroupChatConsumer.broadcast_event(
            NotifyAddedToGroupEvent(payload=test_payload),
            [user_group_name],
        )

        # Receive the event
        event_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )
        assert len(event_messages) == 1

        # Verify connection is still active with ping/pong
        await self.auth_communicator.send_message(PingMessage())
        ping_messages = await self.auth_communicator.receive_all_messages()
        assert ping_messages == [PongMessage()]
