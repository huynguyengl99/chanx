"""
Tests for chanx.core.decorators module.

Tests the ws_handler, event_handler, and channel decorators
which are framework-agnostic.
"""

import inspect
from typing import Any, Literal

import pytest
from chanx.core.decorators import channel, event_handler, ws_handler
from chanx.messages.base import BaseMessage


class DummyMessage(BaseMessage):
    action: Literal["test"] = "test"
    payload: dict[str, Any]


class DummyResponse(BaseMessage):
    action: Literal["test_response"] = "test_response"
    payload: str


class DummyEvent(BaseMessage):
    action: Literal["test_event"] = "test_event"
    payload: dict[str, Any]


class AnotherResponse(BaseMessage):
    action: Literal["another_response"] = "another_response"
    payload: int


class ThirdResponse(BaseMessage):
    action: Literal["third_response"] = "third_response"
    payload: bool


class InvalidMessage:
    """Not a BaseMessage subclass for testing validation."""

    pass


class TestWsHandler:
    """Test the @ws_handler decorator."""

    def test_ws_handler_with_annotated_function(self) -> None:
        """Test ws_handler decorator on properly annotated function."""

        @ws_handler
        async def handle_test(s: Any, message: DummyMessage) -> DummyResponse:
            return DummyResponse(payload="handled")

        # Check that handler info was attached
        assert hasattr(handle_test, "_ws_handler_info")
        handler_info = getattr(handle_test, "_ws_handler_info")

        assert handler_info["action"] == "handle_test"
        assert handler_info["message_action"] == "test"
        assert handler_info["input_type"] == DummyMessage
        assert handler_info["output_type"] == DummyResponse
        assert handler_info["method_name"] == "handle_test"

    def test_ws_handler_with_custom_action(self) -> None:
        """Test ws_handler decorator with custom action name."""

        @ws_handler(action="custom_action")
        async def some_handler(_self: Any, _message: DummyMessage) -> DummyResponse:
            return DummyResponse(payload="custom")

        handler_info = getattr(some_handler, "_ws_handler_info")
        assert handler_info["action"] == "custom_action"
        assert handler_info["method_name"] == "some_handler"
        assert handler_info["message_action"] == "test"

    def test_ws_handler_with_explicit_types(self) -> None:
        """Test ws_handler decorator with explicit input/output types."""

        @ws_handler(input_type=DummyMessage, output_type=DummyResponse)
        async def handle_explicit(_self: Any, _message: Any) -> None:
            pass

        handler_info = getattr(handle_explicit, "_ws_handler_info")
        assert handler_info["input_type"] == DummyMessage
        assert handler_info["output_type"] == DummyResponse

    def test_ws_handler_with_asyncapi_metadata(self) -> None:
        """Test ws_handler decorator with AsyncAPI documentation metadata."""

        @ws_handler(
            description="Test handler description",
            summary="Test summary",
            tags=["test", "api"],
        )
        async def documented_handler(
            _self: Any, _message: DummyMessage
        ) -> DummyResponse:
            return DummyResponse(payload="documented")

        handler_info = getattr(documented_handler, "_ws_handler_info")
        assert handler_info["description"] == "Test handler description"
        assert handler_info["summary"] == "Test summary"
        assert handler_info["tags"] == ["test", "api"]

    def test_ws_handler_invalid_input_type(self) -> None:
        """Test that ws_handler raises error for invalid input type."""

        with pytest.raises(TypeError, match="must be a BaseMessage subclass"):

            @ws_handler(input_type=InvalidMessage)  # type: ignore
            async def invalid_handler(  # pyright: ignore
                _self: Any, _message: Any
            ) -> None:
                pass

    def test_ws_handler_no_input_type_inference(self) -> None:
        """Test that ws_handler raises error when input type cannot be inferred."""

        with pytest.raises(ValueError, match="Must provide input type"):

            @ws_handler
            async def no_params_handler(_self: Any) -> None:  # pyright: ignore
                pass

    def test_ws_handler_preserves_function(self) -> None:
        """Test that ws_handler preserves the original function."""

        @ws_handler
        async def original_function(
            _self: Any, _message: DummyMessage
        ) -> DummyResponse:
            """Original docstring"""
            return DummyResponse(payload="original")

        # Function should still be callable and preserve metadata
        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original docstring"
        assert inspect.iscoroutinefunction(original_function)

    def test_ws_handler_with_union_output_type(self) -> None:
        """Test ws_handler decorator with UnionType output."""

        @ws_handler(output_type=DummyResponse | AnotherResponse)
        async def union_handler(_self: Any, _message: DummyMessage) -> None:
            pass

        handler_info = getattr(union_handler, "_ws_handler_info")
        assert handler_info["output_type"] == DummyResponse | AnotherResponse

    def test_ws_handler_with_list_output_type(self) -> None:
        """Test ws_handler decorator with list of output types."""

        @ws_handler(output_type=[DummyResponse, AnotherResponse])
        async def list_handler(_self: Any, _message: DummyMessage) -> None:
            pass

        handler_info = getattr(list_handler, "_ws_handler_info")
        assert handler_info["output_type"] == [DummyResponse, AnotherResponse]

    def test_ws_handler_with_tuple_output_type(self) -> None:
        """Test ws_handler decorator with tuple of output types."""

        @ws_handler(output_type=(DummyResponse, AnotherResponse, ThirdResponse))
        async def tuple_handler(_self: Any, _message: DummyMessage) -> None:
            pass

        handler_info = getattr(tuple_handler, "_ws_handler_info")
        assert handler_info["output_type"] == (
            DummyResponse,
            AnotherResponse,
            ThirdResponse,
        )


class TestEventHandler:
    """Test the @event_handler decorator."""

    def test_event_handler_basic(self) -> None:
        """Test basic event_handler decorator functionality."""

        @event_handler
        async def handle_test_event(_self: Any, _event: DummyEvent) -> None:
            pass

        assert hasattr(handle_test_event, "_event_handler_info")
        handler_info = getattr(handle_test_event, "_event_handler_info")

        assert handler_info["action"] == "handle_test_event"
        assert handler_info["message_action"] == "test_event"
        assert handler_info["input_type"] == DummyEvent
        assert handler_info["output_type"] is None
        assert handler_info["method_name"] == "handle_test_event"

    def test_event_handler_with_return_type(self) -> None:
        """Test event_handler with return type annotation."""

        @event_handler
        async def handle_event_with_return(
            _self: Any, _event: DummyEvent
        ) -> DummyResponse:
            return DummyResponse(payload="event handled")

        handler_info = getattr(handle_event_with_return, "_event_handler_info")
        assert handler_info["output_type"] == DummyResponse

    def test_event_handler_with_explicit_types(self) -> None:
        """Test event_handler with explicit input/output types."""

        @event_handler(input_type=DummyEvent, output_type=DummyResponse)
        async def explicit_event_handler(_self: Any, _event: Any) -> None:
            pass

        handler_info = getattr(explicit_event_handler, "_event_handler_info")
        assert handler_info["input_type"] == DummyEvent
        assert handler_info["output_type"] == DummyResponse

    def test_event_handler_with_metadata(self) -> None:
        """Test event_handler with AsyncAPI metadata."""

        @event_handler(
            description="Event handler description",
            summary="Event summary",
            tags=["events"],
        )
        async def documented_event_handler(_self: Any, _event: DummyEvent) -> None:
            pass

        handler_info = getattr(documented_event_handler, "_event_handler_info")
        assert handler_info["description"] == "Event handler description"
        assert handler_info["summary"] == "Event summary"
        assert handler_info["tags"] == ["events"]

    def test_event_handler_with_union_output_type(self) -> None:
        """Test event_handler decorator with UnionType output."""

        @event_handler(output_type=DummyResponse | AnotherResponse)
        async def union_event_handler(_self: Any, _event: DummyEvent) -> None:
            pass

        handler_info = getattr(union_event_handler, "_event_handler_info")
        assert handler_info["output_type"] == DummyResponse | AnotherResponse

    def test_event_handler_with_list_output_type(self) -> None:
        """Test event_handler decorator with list of output types."""

        @event_handler(output_type=[DummyResponse, AnotherResponse])
        async def list_event_handler(_self: Any, _event: DummyEvent) -> None:
            pass

        handler_info = getattr(list_event_handler, "_event_handler_info")
        assert handler_info["output_type"] == [DummyResponse, AnotherResponse]

    def test_event_handler_with_tuple_output_type(self) -> None:
        """Test event_handler decorator with tuple of output types."""

        @event_handler(output_type=(DummyResponse, AnotherResponse, ThirdResponse))
        async def tuple_event_handler(_self: Any, _event: DummyEvent) -> None:
            pass

        handler_info = getattr(tuple_event_handler, "_event_handler_info")
        assert handler_info["output_type"] == (
            DummyResponse,
            AnotherResponse,
            ThirdResponse,
        )


class TestChannelDecorator:
    """Test the @channel decorator."""

    def test_channel_decorator_basic(self) -> None:
        """Test basic channel decorator functionality."""

        @channel()
        class TestConsumer:
            pass

        assert hasattr(TestConsumer, "_channel_info")
        channel_info = getattr(TestConsumer, "_channel_info")

        assert channel_info["name"] is None
        assert channel_info["description"] is None
        assert channel_info["tags"] is None

    def test_channel_decorator_with_metadata(self) -> None:
        """Test channel decorator with metadata."""

        @channel(
            name="custom_channel",
            description="Custom channel description",
            tags=["custom", "test"],
        )
        class CustomConsumer:
            """Docstring for consumer"""

            pass

        channel_info = getattr(CustomConsumer, "_channel_info")
        assert channel_info["name"] == "custom_channel"
        assert channel_info["description"] == "Custom channel description"
        assert channel_info["tags"] == ["custom", "test"]

    def test_channel_decorator_preserves_class(self) -> None:
        """Test that channel decorator preserves the original class."""

        @channel(name="test")
        class OriginalClass:
            """Original docstring"""

            def method(self) -> str:
                return "original"

        # Class should be preserved
        assert OriginalClass.__name__ == "OriginalClass"
        assert OriginalClass.__doc__ == "Original docstring"

        # Methods should work
        instance = OriginalClass()
        assert instance.method() == "original"
