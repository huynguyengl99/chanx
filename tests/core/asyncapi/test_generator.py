"""
Tests for chanx.asyncapi.generator module.

Tests the AsyncAPI 3.0 specification generator functionality.
"""

from typing import Any, Literal
from unittest.mock import Mock

from chanx.asyncapi.generator import AsyncAPIGenerator
from chanx.core.decorators import channel, event_handler, ws_handler
from chanx.core.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.routing.discovery import RouteInfo


class DummyMessage(BaseMessage):
    action: Literal["test"] = "test"
    payload: str


class DummyResponse(BaseMessage):
    action: Literal["test_response"] = "test_response"
    payload: dict[str, Any]


class DummyEvent(BaseMessage):
    action: Literal["test_event"] = "test_event"
    payload: int


@channel(name="test_channel", description="Test channel for testing")
class DummyConsumer(AsyncJsonWebsocketConsumer):
    """Test consumer with documentation."""

    @ws_handler(description="Handle test messages", summary="Test handler")
    async def handle_test(self, message: DummyMessage) -> DummyResponse:
        return DummyResponse(payload={"result": "success"})

    @event_handler(description="Handle test events")
    async def handle_test_event(self, event: DummyEvent) -> None:
        pass


class UndocumentedConsumer(AsyncJsonWebsocketConsumer):
    """Consumer without explicit channel documentation."""

    @ws_handler
    async def handle_simple(self, message: DummyMessage) -> None:
        pass


class TestAsyncAPIGenerator:
    """Test the AsyncAPI generator class."""

    def test_generator_initialization(self) -> None:
        """Test generator initialization with default values."""
        routes: list[RouteInfo] = []
        generator = AsyncAPIGenerator(routes)

        assert generator.routes == []
        assert generator.title is not None
        assert generator.version is not None
        assert generator.server_url is not None
        assert generator.server_protocol is not None
        assert generator.channels == {}
        assert generator.operations == {}

    def test_generator_initialization_with_custom_values(self) -> None:
        """Test generator initialization with custom values."""
        routes: list[RouteInfo] = []
        generator = AsyncAPIGenerator(
            routes=routes,
            title="Custom API",
            version="2.0.0",
            description="Custom description",
            server_url="wss://example.com",
            server_protocol="wss",
        )

        assert generator.title == "Custom API"
        assert generator.version == "2.0.0"
        assert generator.description == "Custom description"
        assert generator.server_url == "wss://example.com"
        assert generator.server_protocol == "wss"

    def test_generate_empty_spec(self) -> None:
        """Test generating spec with no routes."""
        generator = AsyncAPIGenerator([])
        spec = generator.generate()

        # Should generate valid AsyncAPI spec structure
        assert spec["asyncapi"] == "3.0.0"
        assert "info" in spec
        assert "servers" in spec
        assert "channels" in spec
        assert "operations" in spec

        # With no routes, channels and operations should be empty
        assert spec["channels"] == {}
        assert spec["operations"] == {}

    def test_generate_with_single_route(self) -> None:
        """Test generating spec with single route."""
        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        spec = generator.generate()

        # Should have channels and operations
        assert len(spec["channels"]) > 0
        assert len(spec["operations"]) > 0

        # Should have proper info
        assert spec["info"]["title"] is not None
        assert spec["info"]["version"] is not None

    def test_generate_with_multiple_routes(self) -> None:
        """Test generating spec with multiple routes."""
        routes = [
            RouteInfo(
                path="/ws/test1",
                handler=Mock(),
                base_url="ws://localhost:8000",
                consumer=DummyConsumer,
            ),
            RouteInfo(
                path="/ws/test2",
                handler=Mock(),
                base_url="ws://localhost:8000",
                consumer=UndocumentedConsumer,
            ),
        ]

        generator = AsyncAPIGenerator(routes)
        spec = generator.generate()

        # Should have multiple channels
        assert len(spec["channels"]) == 2

        # Each route should generate operations
        assert len(spec["operations"]) > 0

    def test_server_environment_name_localhost(self) -> None:
        """Test server environment name generation for localhost."""
        generator = AsyncAPIGenerator([], server_url="ws://localhost:8000")
        env_name = generator._get_server_environment_name()
        assert env_name == "development"

        generator = AsyncAPIGenerator([], server_url="ws://127.0.0.1:9000")
        env_name = generator._get_server_environment_name()
        assert env_name == "development"

    def test_server_environment_name_production(self) -> None:
        """Test server environment name generation for production."""
        generator = AsyncAPIGenerator([], server_url="wss://production.example.com:443")
        env_name = generator._get_server_environment_name()
        assert env_name == "production"

        generator = AsyncAPIGenerator([], server_url="wss://api.mysite.com")
        env_name = generator._get_server_environment_name()
        assert env_name == "production"

    def test_server_environment_name_no_url(self) -> None:
        """Test server environment name when no URL is provided."""
        generator = AsyncAPIGenerator([], server_url=None)
        env_name = generator._get_server_environment_name()
        assert env_name == "development"

    def test_parameter_type_description(self) -> None:
        """Test parameter type description generation."""
        generator = AsyncAPIGenerator([])

        # Test known converter types
        assert generator._get_parameter_type_description("int") == "int"
        assert generator._get_parameter_type_description("str") == "str"
        assert generator._get_parameter_type_description("slug") == "slug"
        assert generator._get_parameter_type_description("uuid") == "uuid"

        # Test regex patterns
        pattern = "[0-9]+"
        result = generator._get_parameter_type_description(pattern)
        assert result == f"regex: {pattern}"

    def test_get_channel_messages(self) -> None:
        """Test getting channel messages from consumer."""
        # First need to register the consumer's messages
        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()  # This populates the message registry

        messages = generator.get_channel_messages(DummyConsumer)
        assert isinstance(messages, dict)
        # Should have message references
        for _msg_name, msg_ref in messages.items():
            assert "$ref" in msg_ref

    def test_build_output(self) -> None:
        """Test building output message reference."""
        generator = AsyncAPIGenerator([])

        # Build output reference for a message type
        output_ref = generator.build_output("test_channel", DummyResponse)

        assert "$ref" in output_ref
        assert "test_channel" in output_ref["$ref"]
        assert "messages" in output_ref["$ref"]

    def test_channel_with_decorator_metadata(self) -> None:
        """Test channel building with @channel decorator metadata."""
        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()

        # Should use decorator name instead of class snake_name
        assert "test_channel" in generator.channels
        channel = generator.channels["test_channel"]
        assert channel["title"] == "test_channel"
        assert channel["description"] == "Test channel for testing"

    def test_build_channels_with_route_info(self) -> None:
        """Test building channels with route information."""
        route = RouteInfo(
            path="/ws/test/{user_id}",
            handler=Mock(),
            base_url="ws://localhost:8000",
            path_params={"user_id": "int"},
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()

        # Should have created channel (using @channel decorator name)
        assert len(generator.channels) == 1
        assert "test_channel" in generator.channels

        channel = generator.channels["test_channel"]
        assert channel["address"] == "/ws/test/{user_id}"

        # Should have path parameters
        assert "parameters" in channel
        assert "user_id" in channel["parameters"]
        assert "description" in channel["parameters"]["user_id"]

    def test_build_operations_with_handlers(self) -> None:
        """Test building operations from consumer handlers."""
        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()  # Build channels first
        generator.build_operations()

        # Should have created operations for each handler
        assert len(generator.operations) > 0

        # Operations should have proper structure
        for _op_name, operation in generator.operations.items():
            assert "action" in operation
            assert operation["action"] in ["send", "receive"]
            assert "channel" in operation
            assert "$ref" in operation["channel"]

    def test_channel_with_path_parameters(self) -> None:
        """Test channel creation with path parameters."""
        route = RouteInfo(
            path="/ws/room/{room_id}/user/{user_id}",
            handler=Mock(),
            base_url="ws://localhost:8000",
            path_params={"room_id": "str", "user_id": "int"},
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()

        channel = generator.channels["test_channel"]
        assert "parameters" in channel
        assert "room_id" in channel["parameters"]
        assert "user_id" in channel["parameters"]

        # Check parameter descriptions contain type info
        room_param = channel["parameters"]["room_id"]
        user_param = channel["parameters"]["user_id"]
        assert "str" in room_param["description"]
        assert "int" in user_param["description"]

    def test_channel_without_decorator(self) -> None:
        """Test channel creation without @channel decorator."""
        route = RouteInfo(
            path="/ws/simple",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=UndocumentedConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()

        # Should use snake_name when no @channel decorator
        assert "undocumented" in generator.channels
        channel = generator.channels["undocumented"]
        assert channel["title"] == "undocumented"

    def test_operation_structure(self) -> None:
        """Test operation structure and content."""
        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()
        generator.build_operations()

        # Check that operations have required fields
        assert len(generator.operations) > 0

        for operation in generator.operations.values():
            assert "action" in operation
            assert "channel" in operation
            assert "description" in operation
            assert "summary" in operation

    def test_operation_with_tags(self) -> None:
        """Test operation creation with tags metadata."""

        class TaggedMessage(BaseMessage):
            action: Literal["tagged"] = "tagged"
            payload: str

        class TaggedConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler(tags=["important", "api"])
            async def handle_tagged(self, message: TaggedMessage) -> None:
                pass

        route = RouteInfo(
            path="/ws/tagged",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=TaggedConsumer,
        )

        generator = AsyncAPIGenerator([route])
        generator.build_channels()
        generator.build_operations()

        # Should have operation with tags
        operations = list(generator.operations.values())
        assert len(operations) > 0

        # Find operation with tags
        tagged_operation = None
        for op in operations:
            if "tags" in op:
                tagged_operation = op
                break

        assert tagged_operation is not None
        assert "tags" in tagged_operation
        assert len(tagged_operation["tags"]) == 2
        assert tagged_operation["tags"][0]["name"] == "important"
        assert tagged_operation["tags"][1]["name"] == "api"


class TestAsyncAPIGeneratorIntegration:
    """Test AsyncAPI generator integration with real consumers."""

    def test_full_generation_with_documented_consumer(self) -> None:
        """Test full spec generation with well-documented consumer."""
        route = RouteInfo(
            path="/ws/chat/{room_id}",
            handler=Mock(),
            base_url="wss://api.example.com",
            path_params={"room_id": "str"},
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator(
            routes=[route],
            title="Chat API",
            version="1.0.0",
            description="WebSocket API for chat functionality",
        )

        spec = generator.generate()

        # Validate overall structure
        assert spec["asyncapi"] == "3.0.0"
        assert spec["info"]["title"] == "Chat API"
        assert spec["info"]["version"] == "1.0.0"
        assert spec["info"]["description"] == "WebSocket API for chat functionality"

        # Should have server information
        assert "servers" in spec
        assert len(spec["servers"]) == 1

        # Should have channels with path parameters
        assert len(spec["channels"]) == 1
        channel_name = list(spec["channels"].keys())[0]
        channel = spec["channels"][channel_name]

        # Should have path parameters
        assert "room_id" in channel["parameters"]
        assert "description" in channel["parameters"]["room_id"]

        # Should have operations
        assert len(spec["operations"]) > 0

    def test_generation_with_multiple_consumers(self) -> None:
        """Test generation with multiple different consumers."""

        class ChatMessage(BaseMessage):
            action: Literal["chat"] = "chat"
            payload: str

        class NotificationMessage(BaseMessage):
            action: Literal["notification"] = "notification"
            payload: dict[str, Any]

        @channel(name="chat", description="Chat channel")
        class ChatConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_chat(self, message: ChatMessage) -> None:
                pass

        @channel(name="notifications", description="Notification channel")
        class NotificationConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_notification(self, message: NotificationMessage) -> None:
                pass

        routes = [
            RouteInfo(
                path="/ws/chat",
                handler=Mock(),
                base_url="ws://localhost:8000",
                consumer=ChatConsumer,
            ),
            RouteInfo(
                path="/ws/notifications",
                handler=Mock(),
                base_url="ws://localhost:8000",
                consumer=NotificationConsumer,
            ),
        ]

        generator = AsyncAPIGenerator(routes)
        spec = generator.generate()

        # Should have two channels
        assert len(spec["channels"]) == 2

        # Should have operations for both consumers
        assert len(spec["operations"]) > 0

        # Channel names should reflect the @channel decorator names
        channel_names = list(spec["channels"].keys())
        assert "chat" in channel_names
        assert "notifications" in channel_names

    def test_generation_with_event_handlers(self) -> None:
        """Test generation including event handlers."""

        class EventMessage(BaseMessage):
            action: Literal["user_joined"] = "user_joined"
            payload: dict[str, str]

        class EventConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_test(self, message: DummyMessage) -> None:
                pass

            @event_handler
            async def handle_user_joined(self, event: EventMessage) -> None:
                pass

        route = RouteInfo(
            path="/ws/events",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=EventConsumer,
        )

        generator = AsyncAPIGenerator([route])
        spec = generator.generate()

        # Should have operations for both ws_handler and event_handler
        operations = spec["operations"]
        operation_names = list(operations.keys())

        # Should have both send/receive for ws_handler and operations for event_handler
        assert len(operation_names) > 0

    def test_spec_serialization(self) -> None:
        """Test that generated spec can be JSON serialized."""
        import json

        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=DummyConsumer,
        )

        generator = AsyncAPIGenerator([route])
        spec = generator.generate()

        # Should be JSON serializable without errors
        json_str = json.dumps(spec)
        assert isinstance(json_str, str)

        # Should be able to deserialize back
        deserialized = json.loads(json_str)
        assert deserialized["asyncapi"] == "3.0.0"


class TestAsyncAPIGeneratorErrorHandling:
    """Test error handling in AsyncAPI generator."""

    def test_generation_with_invalid_consumer(self) -> None:
        """Test generation with consumer that has no message handlers."""

        class EmptyConsumer(AsyncJsonWebsocketConsumer):
            """Consumer with no handlers."""

            pass

        route = RouteInfo(
            path="/ws/test",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=EmptyConsumer,
        )

        generator = AsyncAPIGenerator([route])

        # Should handle gracefully and not crash
        spec = generator.generate()
        assert isinstance(spec, dict)
        assert "asyncapi" in spec
        # Should still have channel but no operations
        assert len(spec["channels"]) == 1
        assert len(spec["operations"]) == 0

    def test_generation_with_minimal_route(self) -> None:
        """Test generation with minimal route information."""

        class MinimalConsumer(AsyncJsonWebsocketConsumer):
            """Consumer with minimal setup."""

            @ws_handler
            async def handle_minimal(self, message: DummyMessage) -> None:
                pass

        route = RouteInfo(
            path="/ws/minimal",
            handler=Mock(),
            base_url="ws://localhost:8000",
            consumer=MinimalConsumer,
        )

        generator = AsyncAPIGenerator([route])
        spec = generator.generate()

        # Should still generate spec
        assert spec["asyncapi"] == "3.0.0"
        assert len(spec["channels"]) >= 1  # Should have at least one channel

    def test_generation_with_malformed_route(self) -> None:
        """Test generation with malformed route information."""
        route = RouteInfo(
            path="", handler=None, base_url="", consumer=DummyConsumer  # Empty path
        )

        generator = AsyncAPIGenerator([route])

        # Should handle gracefully
        spec = generator.generate()
        assert isinstance(spec, dict)
