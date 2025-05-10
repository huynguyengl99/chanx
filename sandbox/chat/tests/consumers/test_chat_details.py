import sys
from typing import Any
from unittest.mock import patch

from rest_framework import status

from asgiref.timeout import timeout as async_timeout
from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import (
    ErrorMessage,
)
from chanx.utils.settings import override_chanx_settings
from chat.messages.chat import (
    JoinGroupMessage,
    JoinGroupPayload,
    MessagePayload,
    NewChatMessage,
)
from chat.models import ChatMember, ChatMessage, GroupChat
from test_utils.testing import WebsocketTestCase

if sys.version_info < (3, 11):
    from asyncio.exceptions import TimeoutError


class TestChatDetailConsumer(WebsocketTestCase):
    def setUp(self) -> None:
        super().setUp()
        # Create a group chat for testing
        # Add the authenticated user as a member
        self.group_chat = GroupChat.objects.create(title="Test Group Chat")
        self.group_chat.users.add(self.user)

        self.ws_path = f"/ws/chat/{self.group_chat.pk}/"

    async def test_connect_successfully_and_send_message(self) -> None:
        """Test connection and sending a message to a group chat"""
        await self.auth_communicator.connect()

        # Check authentication was successful
        await self.auth_communicator.assert_authenticated_status_ok()

        # Test sending a chat message
        message_content = "Hello group chat!"
        await self.auth_communicator.send_message(
            NewChatMessage(payload=MessagePayload(content=message_content))
        )

        # Receive the message that was broadcast
        all_messages = await self.auth_communicator.receive_all_json(wait_group=True)

        # Check the message was received and has the correct content
        assert len(all_messages) == 1
        assert all_messages[0].get("action") == "member_message"
        assert all_messages[0].get("payload", {}).get("content") == message_content

        # Verify the message was stored in the database
        messages = ChatMessage.objects.select_related("sender__user").filter(
            group_chat=self.group_chat
        )
        assert await messages.acount() == 1
        message = await messages.afirst()
        assert message
        assert message.sender
        assert message.sender.user.pk == self.user.pk

    async def test_unauthorized_access(self) -> None:
        """Test that non-members cannot connect to the chat"""
        # Create a new user who is not a member of the group chat
        _, non_member_headers = await self.acreate_user_and_ws_headers()

        non_member_communicator = self.create_communicator(headers=non_member_headers)

        # Try to connect - this should fail
        await non_member_communicator.connect()

        # Check authentication response
        auth = await non_member_communicator.wait_for_auth(max_auth_time=1000)
        assert auth
        assert auth.payload.status_code == status.HTTP_403_FORBIDDEN

        # Connection should be closed
        await non_member_communicator.assert_closed()

    async def test_group_message_broadcast(self) -> None:
        """Test that messages are broadcast to all group members"""
        # Create a second user and make them a member
        second_user, second_ws_headers = await self.acreate_user_and_ws_headers()

        await ChatMember.objects.acreate(
            user=second_user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
        )

        # Create two communicators - one for each user
        first_communicator = self.auth_communicator

        second_communicator = self.create_communicator(
            headers=second_ws_headers,
        )

        # Connect both users
        await first_communicator.connect()
        await first_communicator.assert_authenticated_status_ok()

        await second_communicator.connect()
        await second_communicator.assert_authenticated_status_ok()

        # Send a message from the first user
        message_content = "This is a group message"
        await first_communicator.send_message(
            NewChatMessage(payload=MessagePayload(content=message_content))
        )

        # Get message on first communicator (sender)
        first_messages = await first_communicator.receive_all_json(wait_group=True)
        assert len(first_messages) == 1
        assert first_messages[0].get("action") == "member_message"
        assert first_messages[0].get("payload", {}).get("content") == message_content

        # Second user should also receive the message
        second_messages = await second_communicator.receive_all_json(wait_group=True)
        assert len(second_messages) == 1
        assert second_messages[0].get("action") == "member_message"
        assert second_messages[0].get("payload", {}).get("content") == message_content

    async def test_invalid_message_handling(self) -> None:
        """Test handling of invalid messages"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send an invalid message type
        await self.auth_communicator.send_message(
            BaseMessage(action="invalid_action", payload=None)
        )

        # Should receive an error
        all_json = await self.auth_communicator.receive_all_json()
        error_item = all_json[0]
        error_message = ErrorMessage.model_validate(error_item)
        assert error_message.payload[0]["type"] == "literal_error"

    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_send_with_completion_message(self) -> None:
        """Test that completion messages are sent when enabled"""
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Send a message
        await self.auth_communicator.send_message(
            NewChatMessage(payload=MessagePayload(content="Test completion"))
        )

        all_messages: list[dict[str, Any]] = []
        try:
            async with async_timeout(0.5):
                while True:
                    message = await self.auth_communicator.receive_json_from(0.1)
                    all_messages.append(message)
        except TimeoutError:
            pass

        # Should have at least two messages: the message and a completion
        message_types = [msg.get("action") for msg in all_messages]
        assert "member_message" in message_types
        assert "complete" in message_types

    async def test_exception_during_message_processing(self) -> None:
        """Test exception handling during message processing"""
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Mock the receive_message method to raise an exception
        with patch(
            "chat.consumers.chat_detail.ChatDetailConsumer.receive_message",
            side_effect=Exception("Test exception"),
        ):
            # Send a message that will trigger the exception
            await self.auth_communicator.send_json_to(
                {"action": "new_chat_message", "payload": {"content": "Test message"}}
            )

            # Should receive an error message
            all_messages = await self.auth_communicator.receive_all_json(10)
            error_message = ErrorMessage.model_validate(all_messages[0])
            assert error_message.payload == {"detail": "Failed to process message"}

    @override_chanx_settings(LOG_RECEIVED_MESSAGE=True)
    async def test_message_logging(self) -> None:
        """Test that messages are properly logged"""
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Test with logging
        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            await self.auth_communicator.send_message(
                NewChatMessage(payload=MessagePayload(content="Test logging"))
            )
            await self.auth_communicator.receive_all_json()

            # Should log "Received websocket json"
            assert "Received websocket json" in str(mock_logger.call_args_list)

    async def test_group_message_broadcast_to_specific_groups(self) -> None:
        """Test that messages are broadcast to all group members"""
        # Create a second user and make them a member
        second_user, second_ws_headers = await self.acreate_user_and_ws_headers()
        third_user, third_ws_headers = await self.acreate_user_and_ws_headers()

        await ChatMember.objects.acreate(
            user=second_user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
        )
        await ChatMember.objects.acreate(
            user=third_user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.MEMBER,
        )

        # Create two communicators - one for each user
        first_communicator = self.auth_communicator

        second_communicator = self.create_communicator(
            headers=second_ws_headers,
        )
        third_communicator = self.create_communicator(
            headers=third_ws_headers,
        )

        # Connect both users
        await first_communicator.connect()
        await first_communicator.assert_authenticated_status_ok()

        await second_communicator.connect()
        await second_communicator.assert_authenticated_status_ok()

        await third_communicator.connect()
        await third_communicator.assert_authenticated_status_ok()

        custom_group = "custom_group"

        await first_communicator.send_message(
            JoinGroupMessage(payload=JoinGroupPayload(group_name=custom_group))
        )
        await first_communicator.receive_all_json()
        await third_communicator.send_message(
            JoinGroupMessage(payload=JoinGroupPayload(group_name=custom_group))
        )
        await third_communicator.receive_all_json()

        # Send a message from the first user
        message_content = "This is a group message"
        await first_communicator.send_message(
            NewChatMessage(
                payload=MessagePayload(content=message_content, groups=[custom_group])
            )
        )

        # Get message on first communicator (sender)
        first_messages = await first_communicator.receive_all_json(wait_group=True)
        assert len(first_messages) == 1
        assert first_messages[0].get("action") == "member_message"
        assert first_messages[0].get("payload", {}).get("content") == message_content

        # Second user should not receive the message
        await second_communicator.receive_nothing()

        # Third user should receive the message
        third_messages = await third_communicator.receive_all_json(wait_group=True)
        assert len(third_messages) == 1
        assert third_messages[0].get("action") == "member_message"
        assert third_messages[0].get("payload", {}).get("content") == message_content
