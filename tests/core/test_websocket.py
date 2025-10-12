"""
Tests for chanx.core.websocket module.

Tests the framework-agnostic parts of AsyncJsonWebsocketConsumer
including message processing, type adapter building, and handler routing.
"""

from typing import Any, Literal
from unittest.mock import AsyncMock

import pytest
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import CompleteMessage, ErrorMessage


class DummyMessage(BaseMessage):
    action: Literal["test"] = "test"
    payload: dict[str, Any]


class DummyResponse(BaseMessage):
    action: Literal["test_response"] = "test_response"
    payload: str


class DummyEvent(BaseMessage):
    action: Literal["test_event"] = "test_event"
    payload: dict[str, Any]


class OtherDummyMessage(BaseMessage):
    action: Literal["other"] = "other"
    payload: str


class TestInitSubclass:
    """Test the __init_subclass__ method and type adapter building."""

    def test_empty_consumer_initialization(self) -> None:
        """Test that a consumer without handlers initializes properly."""

        class EmptyConsumer(AsyncJsonWebsocketConsumer):
            pass

        # Should have empty handler maps
        assert EmptyConsumer._MESSAGE_HANDLER_INFO_MAP == {}
        assert EmptyConsumer._EVENT_HANDLER_INFO_MAP == {}

        # Should have adapters (even if empty)
        assert hasattr(EmptyConsumer, "incoming_message_adapter")
        assert hasattr(EmptyConsumer, "incoming_event_adapter")
        assert hasattr(EmptyConsumer, "outgoing_message_adapter")

    def test_consumer_with_handlers_builds_maps(self) -> None:
        """Test that a consumer with handlers builds handler maps correctly."""

        class HandlerConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_test(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="handled")

            @ws_handler
            async def handle_other(self, _message: OtherDummyMessage) -> DummyResponse:
                return DummyResponse(payload="other handled")

            @event_handler
            async def handle_test_event(self, event: DummyEvent) -> None:
                pass

        # Should have populated handler maps
        assert len(HandlerConsumer._MESSAGE_HANDLER_INFO_MAP) == 2
        assert "test" in HandlerConsumer._MESSAGE_HANDLER_INFO_MAP
        assert "other" in HandlerConsumer._MESSAGE_HANDLER_INFO_MAP

        assert len(HandlerConsumer._EVENT_HANDLER_INFO_MAP) == 1
        assert "test_event" in HandlerConsumer._EVENT_HANDLER_INFO_MAP

        # Handler info should be correct
        test_handler_info = HandlerConsumer._MESSAGE_HANDLER_INFO_MAP["test"]
        assert test_handler_info["method_name"] == "handle_test"
        assert test_handler_info["input_type"] == DummyMessage
        assert test_handler_info["output_type"] == DummyResponse

    def test_consumer_name_generation(self) -> None:
        """Test that consumer names are generated correctly."""

        class TestConsumer(AsyncJsonWebsocketConsumer):
            pass

        assert TestConsumer.name == "Test"
        assert TestConsumer.snake_name == "test"

        class MyWebSocketConsumer(AsyncJsonWebsocketConsumer):
            pass

        assert MyWebSocketConsumer.name == "MyWebSocket"
        assert MyWebSocketConsumer.snake_name == "my_web_socket"

    def test_abstract_consumer_skipped(self) -> None:
        """Test that abstract consumers are skipped during initialization."""

        class AbstractAsyncJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
            pass

        # Should not try to process handlers for abstract class
        # This tests the condition in __init_subclass__
        assert hasattr(AbstractAsyncJsonWebsocketConsumer, "_MESSAGE_HANDLER_INFO_MAP")


class TestTypeAdapterBuilding:
    """Test the type adapter building functionality."""

    def test_single_message_type_adapter(self) -> None:
        """Test adapter building with single message type."""

        class SingleMessageConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_test(self, message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="handled")

        # Should be able to validate a test message
        adapter = SingleMessageConsumer.incoming_message_adapter
        validated = adapter.validate_python(
            {"action": "test", "payload": {"key": "value"}}
        )
        assert isinstance(validated, DummyMessage)
        assert validated.action == "test"
        assert validated.payload == {"key": "value"}

    def test_multiple_message_types_adapter(self) -> None:
        """Test adapter building with multiple message types."""

        class MultiMessageConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_test(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="handled")

            @ws_handler
            async def handle_other(self, _message: OtherDummyMessage) -> DummyResponse:
                return DummyResponse(payload="other handled")

        adapter = MultiMessageConsumer.incoming_message_adapter

        # Should validate both message types
        test_msg = adapter.validate_python(
            {"action": "test", "payload": {"key": "value"}}
        )
        assert isinstance(test_msg, DummyMessage)

        other_msg = adapter.validate_python(
            {"action": "other", "payload": "string value"}
        )
        assert isinstance(other_msg, OtherDummyMessage)

    def test_outgoing_adapter_includes_system_messages(self) -> None:
        """Test that outgoing adapter includes system messages."""

        class TestConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_test(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="handled")

        adapter = TestConsumer.outgoing_message_adapter

        # Should be able to validate system messages
        complete_msg = adapter.validate_python({"action": "complete", "payload": None})
        assert isinstance(complete_msg, CompleteMessage)

        error_msg = adapter.validate_python(
            {"action": "error", "payload": {"detail": "test error"}}
        )
        assert isinstance(error_msg, ErrorMessage)

        # Should also validate custom response
        response_msg = adapter.validate_python(
            {"action": "test_response", "payload": "test"}
        )
        assert isinstance(response_msg, DummyResponse)


class TestWebsocketEdgeCases:
    """Test edge cases and error conditions in websocket functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_event_string_groups(self) -> None:
        """Test broadcast_event with string groups parameter."""
        from unittest.mock import Mock

        class TestConsumer(AsyncJsonWebsocketConsumer):
            pass

        # Mock the get_channel_layer directly on TestConsumer
        mock_layer = Mock()
        mock_layer.group_send = AsyncMock()

        # Replace get_channel_layer on the class with a function that returns mock_layer
        TestConsumer.get_channel_layer = lambda alias: mock_layer  # type: ignore[misc, assignment]

        event = DummyMessage(payload={"data": "test"})

        # Test with string group - covers line 618
        await TestConsumer.broadcast_event(event, "single_group")

        # Should have called group_send on the channel layer
        mock_layer.group_send.assert_called_once_with(
            "single_group",
            {
                "type": "handle_channel_event",
                "event_data": event.model_dump(mode="json"),
            },
        )
