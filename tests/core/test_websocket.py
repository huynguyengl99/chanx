"""
Tests for chanx.core.websocket module.

Tests the framework-agnostic parts of AsyncJsonWebsocketConsumer
including message processing, type adapter building, and handler routing.
"""

import re
from typing import Any, ClassVar, Literal
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

        # Adapters should be None when no handlers are registered
        assert EmptyConsumer.incoming_message_adapter is None
        assert EmptyConsumer.incoming_event_adapter is None
        # Outgoing adapter always exists (includes system messages)
        assert EmptyConsumer.outgoing_message_adapter is not None

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
        assert adapter is not None
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
        assert adapter is not None

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


class TestEmptyConsumerRuntime:
    """Test runtime behavior when a consumer has no handlers."""

    @pytest.mark.asyncio
    async def test_handle_json_with_no_message_handlers(self) -> None:
        """handle_json should call handle_json_processing_error when no handlers."""

        class NoHandlerConsumer(AsyncJsonWebsocketConsumer):
            pass

        consumer = NoHandlerConsumer()
        consumer.handle_json_processing_error = AsyncMock()  # type: ignore[method-assign]

        await consumer.handle_json({"action": "test", "payload": {}})

        consumer.handle_json_processing_error.assert_called_once()
        error = consumer.handle_json_processing_error.call_args[0][0]
        assert isinstance(error, RuntimeError)
        assert "No message handlers registered" in str(error)

    @pytest.mark.asyncio
    async def test_handle_channel_event_with_no_event_handlers(self) -> None:
        """handle_channel_event should log and return when no event handlers."""

        class NoHandlerConsumer(AsyncJsonWebsocketConsumer):
            pass

        consumer = NoHandlerConsumer()
        consumer.receive_event = AsyncMock()  # type: ignore[method-assign]

        await consumer.handle_channel_event(
            {"event_data": {"action": "test", "payload": {}}}
        )

        # Should not have reached receive_event
        consumer.receive_event.assert_not_called()

    def test_adapters_none_based_on_handler_type(self) -> None:
        """Adapters should be None only for handler types not registered."""

        class WsOnlyConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_test(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="handled")

        assert WsOnlyConsumer.incoming_message_adapter is not None
        assert WsOnlyConsumer.incoming_event_adapter is None

        class EventOnlyConsumer(AsyncJsonWebsocketConsumer):
            @event_handler
            async def handle_test_event(self, event: DummyEvent) -> None:
                pass

        assert EventOnlyConsumer.incoming_message_adapter is None
        assert EventOnlyConsumer.incoming_event_adapter is not None


class ACreated(BaseMessage):
    action: Literal["a.created"] = "a.created"
    payload: dict[str, Any]


class AChanged(BaseMessage):
    action: Literal["a.changed"] = "a.changed"
    payload: dict[str, Any]


class TestPassthroughEvents:
    """Test the passthrough_events feature."""

    def test_passthrough_registers_handler_info(self) -> None:
        """Test that passthrough_events creates correct handler info entries."""

        class PassthroughConsumer(AsyncJsonWebsocketConsumer):
            passthrough_events = [ACreated, AChanged]

        assert len(PassthroughConsumer._EVENT_HANDLER_INFO_MAP) == 2

        handler_info = PassthroughConsumer._EVENT_HANDLER_INFO_MAP["a.created"]
        assert handler_info["action"] == "handle_passthrough_a_created"
        assert handler_info["message_action"] == "a.created"
        assert handler_info["input_type"] == ACreated
        assert handler_info["output_type"] == ACreated
        assert handler_info["method_name"] == "handle_passthrough_a_created"
        assert handler_info.get("description") == "Passthrough handler for ACreated"

    @pytest.mark.asyncio
    async def test_passthrough_handler_returns_event(self) -> None:
        """Test that the generated passthrough handler returns the event unchanged."""

        class PassthroughConsumer(AsyncJsonWebsocketConsumer):
            passthrough_events = [ACreated]

        consumer = PassthroughConsumer()
        event = ACreated(payload={"id": 1})
        handler = getattr(consumer, "handle_passthrough_a_created")
        result = await handler(event)
        assert result is event

    def test_explicit_event_handler_takes_priority(self) -> None:
        """Test that explicit @event_handler overrides passthrough for same type."""

        class MixedConsumer(AsyncJsonWebsocketConsumer):
            passthrough_events = [ACreated, AChanged]

            @event_handler
            async def handle_a_created(self, event: ACreated) -> ACreated:
                return event

        # ACreated should use the explicit handler, not passthrough
        handler_info = MixedConsumer._EVENT_HANDLER_INFO_MAP["a.created"]
        assert handler_info["method_name"] == "handle_a_created"

        # AChanged should use passthrough
        handler_info = MixedConsumer._EVENT_HANDLER_INFO_MAP["a.changed"]
        assert handler_info["method_name"] == "handle_passthrough_a_changed"

    def test_passthrough_builds_adapters(self) -> None:
        """Test that passthrough events are included in both incoming and outgoing adapters."""

        class PassthroughConsumer(AsyncJsonWebsocketConsumer):
            passthrough_events = [ACreated, AChanged]

        # Incoming event adapter
        adapter = PassthroughConsumer.incoming_event_adapter
        assert adapter is not None
        assert isinstance(
            adapter.validate_python({"action": "a.created", "payload": {"id": 1}}),
            ACreated,
        )
        assert isinstance(
            adapter.validate_python({"action": "a.changed", "payload": {"id": 2}}),
            AChanged,
        )

        # Outgoing message adapter
        assert isinstance(
            PassthroughConsumer.outgoing_message_adapter.validate_python(
                {"action": "a.created", "payload": {"id": 1}}
            ),
            ACreated,
        )

    def test_empty_passthrough_events(self) -> None:
        """Test that empty passthrough_events list works fine."""

        class EmptyPassthroughConsumer(AsyncJsonWebsocketConsumer):
            passthrough_events = []

        assert EmptyPassthroughConsumer._EVENT_HANDLER_INFO_MAP == {}

    def test_custom_passthrough_method_prefix(self) -> None:
        """Test that passthrough_method_prefix can be overridden."""

        class CustomPrefixConsumer(AsyncJsonWebsocketConsumer):
            passthrough_events = [ACreated, AChanged]
            passthrough_method_prefix = "forward_"

        assert hasattr(CustomPrefixConsumer, "forward_a_created")
        assert hasattr(CustomPrefixConsumer, "forward_a_changed")
        assert not hasattr(CustomPrefixConsumer, "handle_passthrough_a_created")

        handler_info = CustomPrefixConsumer._EVENT_HANDLER_INFO_MAP["a.created"]
        assert handler_info["method_name"] == "forward_a_created"
        assert handler_info["action"] == "forward_a_created"

    def test_passthrough_events_merge_across_mro(self) -> None:
        """Test that passthrough_events from mixins and the consumer are merged."""

        class PassthroughMixin:
            passthrough_events: ClassVar[list[type[BaseMessage]]] = [ACreated]

        class MergedConsumer(PassthroughMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            passthrough_events = [AChanged]

        # Both the mixin's and the consumer's passthrough events are present.
        assert set(MergedConsumer._EVENT_HANDLER_INFO_MAP) == {"a.created", "a.changed"}
        assert (
            MergedConsumer._EVENT_HANDLER_INFO_MAP["a.created"]["method_name"]
            == "handle_passthrough_a_created"
        )
        assert (
            MergedConsumer._EVENT_HANDLER_INFO_MAP["a.changed"]["method_name"]
            == "handle_passthrough_a_changed"
        )

    def test_passthrough_events_merge_dedupes(self) -> None:
        """Test that a type declared in both mixin and consumer is not duplicated."""

        class PassthroughMixin:
            passthrough_events: ClassVar[list[type[BaseMessage]]] = [ACreated, AChanged]

        class MergedConsumer(PassthroughMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            passthrough_events = [ACreated]

        assert set(MergedConsumer._EVENT_HANDLER_INFO_MAP) == {"a.created", "a.changed"}

    def test_passthrough_events_validates_base_message_subclass(self) -> None:
        """Test that non-BaseMessage types in passthrough_events raise TypeError."""

        class NotAMessage:
            pass

        with pytest.raises(TypeError, match="must be a BaseMessage subclass"):

            class InvalidConsumer(AsyncJsonWebsocketConsumer):
                passthrough_events = [NotAMessage]  # type: ignore[list-item]

            _ = InvalidConsumer  # used to trigger class creation above


class TestHandlerCollisions:
    """Test that two distinct handlers cannot claim the same action."""

    def test_duplicate_message_action_raises(self) -> None:
        """Test that two ws handlers for one action fail at class definition."""

        class HealthMixin:
            @ws_handler
            async def handle_health_probe(self, _message: DummyMessage) -> None:
                return None

        class EchoMixin:
            @ws_handler
            async def handle_echo_probe(self, _message: DummyMessage) -> None:
                return None

        with pytest.raises(TypeError, match="two message handlers for action 'test'"):

            class CollidingConsumer(HealthMixin, EchoMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
                pass

            _ = CollidingConsumer  # used to trigger class creation above

    def test_duplicate_event_action_raises(self) -> None:
        """Test that two event handlers for one action fail at class definition."""

        class HealthMixin:
            @event_handler
            async def handle_health_event(self, event: DummyEvent) -> None:
                return None

        class EchoMixin:
            @event_handler
            async def handle_echo_event(self, event: DummyEvent) -> None:
                return None

        with pytest.raises(
            TypeError, match="two event handlers for action 'test_event'"
        ):

            class CollidingConsumer(HealthMixin, EchoMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
                pass

            _ = CollidingConsumer  # used to trigger class creation above

    def test_error_message_is_order_independent(self) -> None:
        """Test that the reported method names do not depend on MRO ordering."""

        class HealthMixin:
            @ws_handler
            async def handle_health_probe(self, _message: DummyMessage) -> None:
                return None

        class EchoMixin:
            @ws_handler
            async def handle_echo_probe(self, _message: DummyMessage) -> None:
                return None

        expected = re.escape("handle_echo_probe() and handle_health_probe()")

        with pytest.raises(TypeError, match=expected):

            class OneOrder(HealthMixin, EchoMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
                pass

        with pytest.raises(TypeError, match=expected):

            class OtherOrder(EchoMixin, HealthMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
                pass

    def test_overriding_an_inherited_handler_is_allowed(self) -> None:
        """Test that redefining a handler method in a subclass still works."""

        class ParentConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_dummy(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="parent")

        class ChildConsumer(ParentConsumer):
            @ws_handler
            async def handle_dummy(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="child")

        assert ChildConsumer._MESSAGE_HANDLER_INFO_MAP["test"]["method_name"] == (
            "handle_dummy"
        )

    def test_overriding_a_mixin_handler_is_allowed(self) -> None:
        """Test that a consumer can override a handler contributed by a mixin."""

        class DummyMixin:
            @ws_handler
            async def handle_dummy(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="mixin")

        class OverridingConsumer(DummyMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            @ws_handler
            async def handle_dummy(self, _message: DummyMessage) -> DummyResponse:
                return DummyResponse(payload="consumer")

        assert set(OverridingConsumer._MESSAGE_HANDLER_INFO_MAP) == {"test"}


class TestExtraGroups:
    """Test the extra_groups feature and per-instance groups isolation."""

    def test_extra_groups_merge_across_mro(self) -> None:
        """Test that extra_groups from every mixin land on the instance."""

        class HealthMixin:
            extra_groups: ClassVar[list[str]] = ["health_group"]

        class EchoMixin:
            extra_groups: ClassVar[list[str]] = ["echo_group"]

        class GatewayConsumer(HealthMixin, EchoMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            extra_groups = ["gateway_group"]

        consumer = GatewayConsumer()
        assert consumer.groups == ["gateway_group", "health_group", "echo_group"]

    def test_extra_groups_merge_dedupes(self) -> None:
        """Test that a group declared in both mixin and consumer appears once."""

        class SharedMixin:
            extra_groups: ClassVar[list[str]] = ["shared_group", "mixin_group"]

        class MergedConsumer(SharedMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            extra_groups = ["shared_group"]

        assert MergedConsumer().groups == ["shared_group", "mixin_group"]

    def test_extra_groups_union_with_declared_groups(self) -> None:
        """Test that extra_groups are appended to a framework-owned groups list."""

        class NotifyMixin:
            extra_groups: ClassVar[list[str]] = ["notify_group"]

        class MergedConsumer(NotifyMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            groups = ["static_group"]

        assert MergedConsumer().groups == ["static_group", "notify_group"]

    def test_groups_keeps_mro_shadowing(self) -> None:
        """Test that `groups` still shadows normally, so a subclass can narrow it."""

        class BaseConsumer(AsyncJsonWebsocketConsumer):
            groups = ["parent_group"]

        class NarrowedConsumer(BaseConsumer):
            groups = ["child_group"]

        assert NarrowedConsumer().groups == ["child_group"]

    def test_broadcast_default_groups_include_extras(self) -> None:
        """Test that broadcast_event's default targets match what instances join."""

        class NotifyMixin:
            extra_groups: ClassVar[list[str]] = ["notify_group"]

        class MergedConsumer(NotifyMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
            groups = ["static_group"]

        assert MergedConsumer._default_groups() == MergedConsumer().groups

    def test_default_groups_without_declared_groups(self) -> None:
        """Test that a consumer never declaring `groups` still resolves defaults."""

        class BareConsumer(AsyncJsonWebsocketConsumer):
            pass

        assert BareConsumer._default_groups() == []

    def test_groups_set_before_super_init_is_preserved(self) -> None:
        """Test that a consumer assigning self.groups in __init__ is not clobbered."""

        class CustomInitConsumer(AsyncJsonWebsocketConsumer):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.groups = ["from_init"]
                super().__init__(*args, **kwargs)

        assert CustomInitConsumer().groups == ["from_init"]

    def test_runtime_group_mutation_is_per_instance(self) -> None:
        """Test that appending to self.groups does not leak into the class attribute."""

        class StaticGroupConsumer(AsyncJsonWebsocketConsumer):
            groups = ["static_group"]

        first = StaticGroupConsumer()
        first.groups.append("per_connection_group")

        assert StaticGroupConsumer.groups == ["static_group"]
        assert StaticGroupConsumer().groups == ["static_group"]


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
