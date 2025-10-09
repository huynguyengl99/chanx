"""
Tests for chanx.core.registry module.

Tests the message registry functionality.
"""

from typing import Any, Literal

from chanx.core.registry import MessageRegistry
from chanx.messages.base import BaseMessage
from pydantic import BaseModel
from typing_extensions import TypedDict


class DummyMessage(BaseMessage):
    action: Literal["test"] = "test"
    payload: str


class OtherDummyMessage(BaseMessage):
    action: Literal["other"] = "other"
    payload: int


class Address(BaseModel):
    street: str
    city: str


class Payload(BaseModel):
    pk: int
    data: dict[str, Any]
    address: Address | str


class RefDummyMessage(BaseMessage):
    action: Literal["ref_dummy"] = "ref_dummy"
    payload: Payload


class TestMessageRegistry:
    """Test the MessageRegistry class."""

    def test_registry_initialization(self) -> None:
        """Test that registry initializes with empty collections."""
        registry = MessageRegistry()

        assert registry.schemas == {}
        assert registry.messages == {}
        assert registry.schema_objects == {}
        assert registry.message_objects == {}

    def test_build_messages(self) -> None:
        """Test adding message types to the registry."""
        registry = MessageRegistry()

        registry.add(DummyMessage, "TestConsumer")
        registry.add(OtherDummyMessage, "TestConsumer")
        registry.add(RefDummyMessage, "TestConsumer")
        registry.add(DummyMessage, "OtherConsumer")

        # Should be registered in consumer_messages
        assert registry.messages == {
            DummyMessage: "#/components/messages/dummy_message",
            OtherDummyMessage: "#/components/messages/other_dummy_message",
            RefDummyMessage: "#/components/messages/ref_dummy_message",
        }
        assert registry.schemas == {
            DummyMessage: "#/components/schemas/DummyMessage",
            OtherDummyMessage: "#/components/schemas/OtherDummyMessage",
            Address: "#/components/schemas/Address",
            Payload: "#/components/schemas/Payload",
            RefDummyMessage: "#/components/schemas/RefDummyMessage",
        }

        assert registry.schema_objects == {
            "Address": {
                "properties": {
                    "city": {"title": "City", "type": "string"},
                    "street": {"title": "Street", "type": "string"},
                },
                "required": ["street", "city"],
                "title": "Address",
                "type": "object",
            },
            "DummyMessage": {
                "properties": {
                    "action": {
                        "const": "test",
                        "default": "test",
                        "title": "Action",
                        "type": "string",
                    },
                    "payload": {"title": "Payload", "type": "string"},
                },
                "required": ["payload"],
                "title": "DummyMessage",
                "type": "object",
            },
            "OtherDummyMessage": {
                "properties": {
                    "action": {
                        "const": "other",
                        "default": "other",
                        "title": "Action",
                        "type": "string",
                    },
                    "payload": {"title": "Payload", "type": "integer"},
                },
                "required": ["payload"],
                "title": "OtherDummyMessage",
                "type": "object",
            },
            "Payload": {
                "properties": {
                    "address": {
                        "anyOf": [
                            {"$ref": "#/components/schemas/Address"},
                            {"type": "string"},
                        ],
                        "title": "Address",
                    },
                    "data": {
                        "additionalProperties": True,
                        "title": "Data",
                        "type": "object",
                    },
                    "pk": {"title": "Pk", "type": "integer"},
                },
                "required": ["pk", "data", "address"],
                "title": "Payload",
                "type": "object",
            },
            "RefDummyMessage": {
                "properties": {
                    "action": {
                        "const": "ref_dummy",
                        "default": "ref_dummy",
                        "title": "Action",
                        "type": "string",
                    },
                    "payload": {"$ref": "#/components/schemas/Payload"},
                },
                "required": ["payload"],
                "title": "RefDummyMessage",
                "type": "object",
            },
        }

        assert registry.message_objects == {
            "dummy_message": {"payload": {"$ref": "#/components/schemas/DummyMessage"}},
            "other_dummy_message": {
                "payload": {"$ref": "#/components/schemas/OtherDummyMessage"}
            },
            "ref_dummy_message": {
                "payload": {"$ref": "#/components/schemas/RefDummyMessage"}
            },
        }

        assert dict(registry.consumer_messages) == {
            "TestConsumer": {RefDummyMessage, DummyMessage, OtherDummyMessage},
            "OtherConsumer": {DummyMessage},
        }

    def test_build_messages_with_typeddict(self) -> None:
        """Test adding message types with TypedDict payloads to the registry."""

        class BaseMessageDict(TypedDict):
            """Base message dict."""

            id: int
            message_type: str
            content: str

        class UserMessageDict(BaseMessageDict):
            """User message dict extends base."""

            author: int
            fuid: str

        class TypedDictMessage(BaseMessage):
            action: Literal["typed_dict_test"] = "typed_dict_test"
            payload: UserMessageDict

        registry = MessageRegistry()
        registry.add(TypedDictMessage, "TestConsumer")

        # Should have registered the message
        assert TypedDictMessage in registry.messages
        assert (
            registry.messages[TypedDictMessage]
            == "#/components/messages/typed_dict_message"
        )

        # Should have registered the TypedDictMessage schema
        assert TypedDictMessage in registry.schemas
        assert (
            registry.schemas[TypedDictMessage]
            == "#/components/schemas/TypedDictMessage"
        )

        # The schema should have proper references to UserMessageDict
        schema = registry.schema_objects["TypedDictMessage"]
        assert (
            schema["properties"]["payload"]["$ref"]
            == "#/components/schemas/UserMessageDict"
        )

        # UserMessageDict should be registered as a separate schema
        assert "UserMessageDict" in registry.schema_objects
        user_msg_schema = registry.schema_objects["UserMessageDict"]

        # Verify UserMessageDict has all required fields
        assert "id" in user_msg_schema["properties"]
        assert "message_type" in user_msg_schema["properties"]
        assert "content" in user_msg_schema["properties"]
        assert "author" in user_msg_schema["properties"]
        assert "fuid" in user_msg_schema["properties"]

        # Verify no $defs references remain in the schema
        import json

        schema_json = json.dumps(registry.schema_objects)
        assert "#/$defs/" not in schema_json, "Found $defs references in schema"
