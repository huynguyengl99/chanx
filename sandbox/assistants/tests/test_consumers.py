import sys
from typing import Any
from unittest.mock import Mock, patch
from uuid import uuid4

from django.conf import settings
from rest_framework import status

import pytest
from asgiref.timeout import timeout as async_timeout
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import (
    ErrorMessage,
    PongMessage,
)
from chanx.settings import chanx_settings
from chanx.utils.settings import override_chanx_settings
from test_utils.testing import WebsocketTestCase

from assistants.messages.assistant import (
    MessagePayload,
    NewMessage,
    ReplyMessage,
    StreamingMessage,
    StreamingReplyCompleteMessage,
    StreamingReplyMessage,
)
from assistants.utils import tokenize_for_streaming

if sys.version_info < (3, 11):
    from asyncio.exceptions import TimeoutError


class TestChatConsumer(WebsocketTestCase):
    ws_path = "/ws/assistants/"

    async def test_connect_successfully_and_send_and_reply_message(self) -> None:
        # Test basic connection and message flow
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth()
        assert auth
        assert auth.payload.status_code == status.HTTP_200_OK

        # Test ping/pong
        await self.auth_communicator.send_message(PingMessage())
        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [PongMessage().model_dump()]

        # Test chat functionality
        message_content = "My message content"
        await self.auth_communicator.send_message(
            NewMessage(payload=MessagePayload(content=message_content))
        )

        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [
            ReplyMessage(
                payload=MessagePayload(content=f"Reply: {message_content}")
            ).model_dump()
        ]

        # Test invalid message handling
        await self.auth_communicator.send_message(
            BaseMessage(action="Invalid action", payload=None)
        )
        all_json = await self.auth_communicator.receive_all_json()
        error_item = all_json[0]
        error_message = ErrorMessage.model_validate(error_item)
        assert error_message.payload[0]["type"] == "union_tag_invalid"
        assert error_message.payload[0]["msg"] == (
            "Input tag 'Invalid action' found using 'action' does not match any of the expected tags: 'new_message', 'ping', 'streaming'"
        )

        await self.auth_communicator.disconnect()

    async def test_exception_during_message_processing(self) -> None:
        # Test exception handling during message processing
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Mock the receive_message method to raise an exception
        with patch(
            "assistants.consumers.AssistantConsumer.receive_message",
            side_effect=Exception("Test exception"),
        ):
            # Send a message that will trigger the exception
            await self.auth_communicator.send_json_to(
                {"action": "new_message", "payload": {"content": "Test message"}}
            )

            # Should receive an error message
            all_messages = await self.auth_communicator.receive_all_json(10)
            error_message = ErrorMessage.model_validate(all_messages[0])
            assert error_message.payload == {"detail": "Failed to process message"}

    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_send_with_completion_message(self) -> None:
        # Test that completion messages are sent when enabled
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Send a message that should trigger a completion
        await self.auth_communicator.send_message(PingMessage())

        all_messages: list[dict[str, Any]] = []
        try:
            async with async_timeout(0.5):
                while True:
                    message: dict[str, Any] = (
                        await self.auth_communicator.receive_json_from(0.1)
                    )
                    all_messages.append(message)
        except TimeoutError:
            pass
        # Should receive the normal response and a completion message
        message_types = [msg.get("action") for msg in all_messages]

        assert "pong" in message_types
        assert "complete" in message_types

    @override_chanx_settings(SEND_COMPLETION=False)
    async def test_send_without_completion_message(self) -> None:
        # Test that completion messages won't be sent when disabled
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Send a message that should trigger a completion
        await self.auth_communicator.send_message(PingMessage())

        assert not chanx_settings.SEND_COMPLETION

        all_messages: list[dict[str, Any]] = []
        try:
            async with async_timeout(0.5):
                while True:
                    message = await self.auth_communicator.receive_json_from(0.1)
                    all_messages.append(message)
        except TimeoutError:
            pass
        # Should receive the normal response and a completion message
        message_types = [msg.get("action") for msg in all_messages]

        assert "pong" in message_types
        assert "complete" not in message_types

    @override_chanx_settings(SEND_MESSAGE_IMMEDIATELY=True)
    async def test_send_message_immediately(self) -> None:
        # Test the send_message_immediately flag
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Monitor asyncio.sleep calls
        with patch("asyncio.sleep") as mock_sleep:
            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_json()
            # Should not call sleep when send_message_immediately is False
            mock_sleep.assert_called()

    @override_chanx_settings(SEND_MESSAGE_IMMEDIATELY=False)
    async def test_send_message_not_immediately(self) -> None:
        # Test the send_message_immediately flag
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Monitor asyncio.sleep calls
        with patch("asyncio.sleep") as mock_sleep:
            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_json()
            # Should not call sleep when send_message_immediately is False
            mock_sleep.assert_not_called()

    async def test_websocket_disconnect(self) -> None:
        # Test disconnection handling
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Monitor logging during disconnect
        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            await self.auth_communicator.disconnect()
            # Should log disconnection
            mock_logger.assert_called_with("Disconnecting websocket")

    async def test_validation_error_handling(self) -> None:
        # Test handling of validation errors
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Send an invalid message format to trigger validation error
        await self.auth_communicator.send_json_to(
            {
                "action": "new_message",
                "payload": {
                    # Missing required 'content' field
                },
            }
        )

        # Should receive validation error
        all_messages = await self.auth_communicator.receive_all_json()
        error_message = ErrorMessage.model_validate(all_messages[0])

        # Check that we received a validation error response
        assert len(error_message.payload) > 0
        assert any("missing" in str(error).lower() for error in error_message.payload)

    async def test_message_id_and_logging(self) -> None:
        # Test message ID generation and logging
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Monitor UUID generation
        uuid = uuid4()
        with patch("uuid.uuid4", return_value=uuid):
            # Monitor contextvars binding
            with patch("structlog.contextvars.bind_contextvars") as mock_bind:
                await self.auth_communicator.send_message(PingMessage())
                await self.auth_communicator.receive_all_json()

                # Should bind message_id and received_action
                mock_bind.assert_called_with(
                    message_id=str(uuid)[:8], received_action="ping"
                )

    @override_chanx_settings(SEND_AUTHENTICATION_MESSAGE=False)
    async def test_authentication_skip(self) -> None:
        # Test behavior when authentication messages are disabled
        await self.auth_communicator.connect()

        # Should not receive auth message
        with pytest.raises(TimeoutError):
            await self.auth_communicator.receive_json_from(timeout=0.1)

    @override_chanx_settings(LOG_RECEIVED_MESSAGE=False)
    async def test_disable_received_message_logging(self) -> None:
        # Test that log_received_message setting works
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            await self.auth_communicator.send_message(PingMessage())

            # Should not log "Received websocket json"
            assert "Received websocket json" not in str(mock_logger.call_args_list)

    @override_chanx_settings(LOG_RECEIVED_MESSAGE=True)
    async def test_enable_received_message_logging(self) -> None:
        # Test that log_received_message setting works
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_json()

            # Should log "Received websocket json"
            assert "Received websocket json" in str(mock_logger.call_args_list)

    @override_chanx_settings(LOG_SENT_MESSAGE=False)
    async def test_disable_sent_message_logging(self) -> None:
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_json()

            # Should not log "Sent websocket json"
            assert "Sent websocket json" not in str(mock_logger.call_args_list)

    @override_chanx_settings(LOG_SENT_MESSAGE=True)
    async def test_enable_sent_message_logging(self) -> None:
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_json()

            # Should log "Sent websocket json"
            assert "Sent websocket json" in str(mock_logger.call_args_list)

    @override_chanx_settings(LOG_IGNORED_ACTIONS={"ping"})
    async def test_ignore_actions(self) -> None:
        # Test silent actions feature by patching the consumer class
        await self.auth_communicator.connect()
        await self.auth_communicator.wait_for_auth()

        # Patch the silent_actions set to include 'ping'
        with patch("chanx.utils.logging.logger.ainfo") as mock_logger:
            # Reset mock_logger to clear previous calls
            mock_logger.reset_mock()

            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_json()

            # Should not log received message for silent action
            assert "ping" not in str(mock_logger.call_args_list)

    async def test_unauthorized_connection(self) -> None:
        # Test anonymous connection
        anonymous_communicator = self.create_communicator(
            headers=[
                (b"origin", settings.SERVER_URL.encode()),
            ]
        )
        await anonymous_communicator.connect()
        await anonymous_communicator.assert_authenticated_status_ok()

        # Test chat functionality
        message_content = "My message content"
        await anonymous_communicator.send_message(
            NewMessage(payload=MessagePayload(content=message_content))
        )

        all_messages = await anonymous_communicator.receive_all_json()
        assert all_messages == [
            ReplyMessage(
                payload=MessagePayload(content=f"Reply: {message_content}")
            ).model_dump()
        ]

    @patch("assistants.consumers.uuid.uuid4", return_value="uuid-mock")
    async def test_connect_successfully_and_send_streaming_message(
        self, _mock_uuid: Mock
    ) -> None:
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth()
        assert auth
        assert auth.payload.status_code == status.HTTP_200_OK

        # Test ping/pong
        await self.auth_communicator.send_message(PingMessage())
        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [PongMessage().model_dump()]

        # Test chat functionality
        message_content = "Hello, this is my streaming message content"
        await self.auth_communicator.send_message(
            StreamingMessage(payload=MessagePayload(content=message_content))
        )

        all_messages = await self.auth_communicator.receive_until_action(
            "streaming_reply_complete", inclusive=True
        )

        streaming_tokens = tokenize_for_streaming(message_content)
        streaming_messages = [
            StreamingReplyMessage(
                payload=StreamingReplyMessage.Payload(content=token, id="uuid-mock")
            ).model_dump()
            for token in streaming_tokens
        ]
        assert all_messages == [
            *streaming_messages,
            StreamingReplyCompleteMessage(
                payload=StreamingReplyCompleteMessage.Payload(id="uuid-mock"),
            ).model_dump(),
        ]
