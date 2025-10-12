"""
Tests for Channels-specific WebSocket functionality.

Tests the integration between chanx.core.websocket and Django Channels,
including the testing framework and routing.
"""

from typing import Any, Literal

from channels.routing import URLRouter

from chanx.channels.routing import path
from chanx.channels.testing import WebsocketTestCase
from chanx.channels.utils.settings import override_chanx_settings
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.constants import GROUP_ACTION_COMPLETE
from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from pydantic import BaseModel
from structlog.testing import capture_logs


class CustomMessage(BaseMessage):
    action: Literal["custom"] = "custom"
    payload: dict[str, Any]


class CustomResponse(BaseMessage):
    action: Literal["custom_response"] = "custom_response"
    payload: str


class CustomBroadcastMessage(BaseMessage):
    action: Literal["broadcast"] = "broadcast"
    payload: str


class CustomBroadcastResponse(BaseMessage):
    action: Literal["broadcast_response"] = "broadcast_response"
    payload: str


class NestedPayload(BaseModel):
    first_field: str
    other_field: int


class NestedMessage(BaseMessage):
    action: Literal["nested"] = "nested"
    payload: NestedPayload


class NestedResponse(BaseMessage):
    action: Literal["nested_response"] = "nested_response"
    payload: NestedPayload


class CustomEvent(BaseMessage):
    action: Literal["test_event"] = "test_event"
    payload: dict[str, Any]


class ChannelsBasedConsumer(AsyncJsonWebsocketConsumer):
    """Consumer using Channels-specific features."""

    groups = ["test_group"]
    authenticator_class = None  # No authentication for tests

    @ws_handler
    async def handle_ping(self, message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler
    async def handle_custom(self, message: CustomMessage) -> CustomResponse:
        return CustomResponse(payload=f"Processed: {message.payload}")

    @ws_handler
    async def handle_nested(self, message: NestedMessage) -> NestedResponse:
        payload = message.payload
        payload.first_field = f"Processed: {payload.first_field}"
        return NestedResponse(payload=payload)

    @ws_handler(output_type=CustomBroadcastResponse)
    async def handle_broadcast(self, message: CustomBroadcastMessage) -> None:
        await self.broadcast_message(
            CustomBroadcastResponse(payload=f"Broadcasted: {message.payload}")
        )

    @event_handler
    async def handle_test_event(self, event: CustomEvent) -> None:
        await self.send_message(
            CustomResponse(payload=f"Event received: {event.payload}")
        )


class TestChannelsWebsocket(WebsocketTestCase):
    """Test Channels-specific WebSocket functionality."""

    ws_path = "/channels-consumer/"
    router = URLRouter([path("channels-consumer/", ChannelsBasedConsumer.as_asgi())])
    consumer = ChannelsBasedConsumer

    async def test_websocket_connection_lifecycle(self) -> None:
        """Test WebSocket connection and disconnection."""
        # Test connection
        await self.auth_communicator.connect()

        # Test that consumer can send messages
        await self.auth_communicator.send_message(PingMessage())
        response = await self.auth_communicator.receive_json_from()

        expected = PongMessage().model_dump()
        assert response == expected

        # Test disconnection
        await self.auth_communicator.disconnect()

    async def test_send_custom_message(self) -> None:
        """Test that decorator-based message routing works with Channels."""
        await self.auth_communicator.connect()

        # Test ping handler
        await self.auth_communicator.send_message(PingMessage())
        responses = await self.auth_communicator.receive_all_messages()
        assert responses == [PongMessage()]

        # Test custom handler
        test_payload = {"key": "value", "number": 42}
        await self.auth_communicator.send_message(CustomMessage(payload=test_payload))
        responses = await self.auth_communicator.receive_all_messages()
        assert responses == [CustomResponse(payload=f"Processed: {test_payload}")]

    async def test_validation_error_handling(self) -> None:
        """Test that validation errors are handled properly in Channels context."""
        await self.auth_communicator.connect()

        # Send invalid message
        await self.auth_communicator.send_json_to(
            {"action": "nonexistent_action", "payload": "test"}
        )

        responses = await self.auth_communicator.receive_all_messages()
        assert responses[0].action == "error"

    async def test_group_messaging(self) -> None:
        """Test group messaging functionality."""
        await self.auth_communicator.connect()

        # Test broadcasting to group
        broadcast_content = "message to broadcast"
        broadcast_message = CustomBroadcastMessage(payload=broadcast_content)

        await self.auth_communicator.send_message(broadcast_message)

        responses = await self.auth_communicator.receive_all_messages(
            stop_action=GROUP_ACTION_COMPLETE
        )

        assert responses == [
            CustomBroadcastResponse(payload=f"Broadcasted: {broadcast_content}")
        ]

    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_completion_message_is_sent(self) -> None:
        """Test completion messages work with Channels."""
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(PingMessage())

        # Should receive both response and completion
        messages = await self.auth_communicator.receive_all_json()
        assert len(messages) >= 2

        # Last message should be completion
        completion_msg = messages[-1]
        assert completion_msg["action"] == "complete"

    @override_chanx_settings(SEND_COMPLETION=False)
    async def test_completion_message_is_not_sent(self) -> None:
        """Test completion messages work with Channels."""
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(PingMessage())

        # Should receive both response and completion
        messages = await self.auth_communicator.receive_all_json()
        assert len(messages) == 1

        # Last message should be completion
        completion_msg = messages[-1]
        assert completion_msg["action"] != "complete"

    @override_chanx_settings(CAMELIZE=True)
    async def test_camelization(self) -> None:
        """Test that camelization works with Channels WebSocket testing."""
        await self.auth_communicator.connect()

        test_payload = NestedPayload(first_field="test", other_field=2)

        await self.auth_communicator.send_message(NestedMessage(payload=test_payload))
        response = await self.auth_communicator.receive_json_from()
        assert "first_field" not in str(response)
        assert "firstField" in str(response)

    @override_chanx_settings(CAMELIZE=False)
    async def test_no_camelization(self) -> None:
        """Test that camelization works with Channels WebSocket testing."""
        await self.auth_communicator.connect()

        test_payload = NestedPayload(first_field="test", other_field=2)

        await self.auth_communicator.send_message(NestedMessage(payload=test_payload))
        response = await self.auth_communicator.receive_json_from()
        assert "first_field" in str(response)
        assert "firstField" not in str(response)

    @override_chanx_settings(LOG_RECEIVED_MESSAGE=True, LOG_SENT_MESSAGE=True)
    async def test_logging_integration(self) -> None:
        """Test that logging works with Channels."""
        await self.auth_communicator.connect()

        with capture_logs() as cap_logs:
            await self.auth_communicator.send_message(PingMessage())
            await self.auth_communicator.receive_all_messages()

        # Should have logs for received and sent messages
        log_events = [log.get("event", "") for log in cap_logs]
        assert log_events == [
            "Websocket received",
            "Websocket sent",
        ]


class ErrorHandlingConsumer(AsyncJsonWebsocketConsumer):
    """Consumer that simulates various error conditions."""

    @ws_handler
    async def handle_ping(self, message: PingMessage) -> PongMessage:
        raise ValueError("Simulated handler error")


class TestChannelsErrorHandling(WebsocketTestCase):
    """Test error handling in Channels context."""

    ws_path = "/error-consumer/"
    router = URLRouter([path("error-consumer/", ErrorHandlingConsumer.as_asgi())])
    consumer = ErrorHandlingConsumer

    async def test_handler_exception_sends_error_response(self) -> None:
        """Test that handler exceptions result in error responses."""
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(PingMessage())
        response = await self.auth_communicator.receive_json_from()

        # Should receive error message
        assert response["action"] == "error"
