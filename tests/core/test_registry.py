"""
Tests for chanx.core.registry module.

Tests the message registry functionality.
"""

import json
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


class ThirdDummyMessage(BaseMessage):
    action: Literal["third"] = "third"
    payload: bool


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

    def test_build_messages_with_nested_typeddict(self) -> None:
        """Test adding message types with nested TypedDict payloads to the registry."""

        class AddressDict(TypedDict):
            """Address information."""

            street: str
            city: str
            country: str

        class ContactDict(TypedDict):
            """Contact information with address."""

            email: str
            phone: str
            address: AddressDict

        class UserProfileDict(TypedDict):
            """User profile with nested contact."""

            id: int
            name: str
            contact: ContactDict

        class NestedTypedDictMessage(BaseMessage):
            action: Literal["nested_typed_dict_test"] = "nested_typed_dict_test"
            payload: UserProfileDict

        registry = MessageRegistry()
        registry.add(NestedTypedDictMessage, "TestConsumer")

        # Should have registered the message
        assert NestedTypedDictMessage in registry.messages
        assert (
            registry.messages[NestedTypedDictMessage]
            == "#/components/messages/nested_typed_dict_message"
        )

        # Should have registered all schemas
        assert NestedTypedDictMessage in registry.schemas
        assert "NestedTypedDictMessage" in registry.schema_objects
        assert "UserProfileDict" in registry.schema_objects
        assert "ContactDict" in registry.schema_objects
        assert "AddressDict" in registry.schema_objects

        # Check that the main message schema references UserProfileDict correctly
        message_schema = registry.schema_objects["NestedTypedDictMessage"]
        assert (
            message_schema["properties"]["payload"]["$ref"]
            == "#/components/schemas/UserProfileDict"
        )

        # Check that UserProfileDict references ContactDict correctly
        user_profile_schema = registry.schema_objects["UserProfileDict"]
        assert (
            user_profile_schema["properties"]["contact"]["$ref"]
            == "#/components/schemas/ContactDict"
        )

        # Check that ContactDict references AddressDict correctly
        contact_schema = registry.schema_objects["ContactDict"]
        assert (
            contact_schema["properties"]["address"]["$ref"]
            == "#/components/schemas/AddressDict"
        )

        # Verify AddressDict has the correct properties
        address_schema = registry.schema_objects["AddressDict"]
        assert "street" in address_schema["properties"]
        assert "city" in address_schema["properties"]
        assert "country" in address_schema["properties"]

        # Verify no $defs references remain anywhere in the schema

        schema_json = json.dumps(registry.schema_objects)
        assert "#/$defs/" not in schema_json, "Found $defs references in nested schema"

    def test_build_messages_with_union_type(self) -> None:
        """Test adding message types with UnionType to the registry."""
        registry = MessageRegistry()

        # Test with UnionType
        union_type = DummyMessage | OtherDummyMessage
        registry.add(union_type, "TestConsumer")

        # Both message types should be registered
        assert DummyMessage in registry.messages
        assert OtherDummyMessage in registry.messages
        assert registry.messages[DummyMessage] == "#/components/messages/dummy_message"
        assert (
            registry.messages[OtherDummyMessage]
            == "#/components/messages/other_dummy_message"
        )

        # Both should be in the consumer messages
        assert DummyMessage in registry.consumer_messages["TestConsumer"]
        assert OtherDummyMessage in registry.consumer_messages["TestConsumer"]

    def test_build_messages_with_list_type(self) -> None:
        """Test adding message types as list to the registry."""
        registry = MessageRegistry()

        # Test with list of types
        list_types: list[type[BaseMessage]] = [
            DummyMessage,
            OtherDummyMessage,
            ThirdDummyMessage,
        ]
        registry.add(list_types, "TestConsumer")

        # All message types should be registered
        assert DummyMessage in registry.messages
        assert OtherDummyMessage in registry.messages
        assert ThirdDummyMessage in registry.messages

        assert registry.messages[DummyMessage] == "#/components/messages/dummy_message"
        assert (
            registry.messages[OtherDummyMessage]
            == "#/components/messages/other_dummy_message"
        )
        assert (
            registry.messages[ThirdDummyMessage]
            == "#/components/messages/third_dummy_message"
        )

        # All should be in the consumer messages
        assert DummyMessage in registry.consumer_messages["TestConsumer"]
        assert OtherDummyMessage in registry.consumer_messages["TestConsumer"]
        assert ThirdDummyMessage in registry.consumer_messages["TestConsumer"]

    def test_build_messages_with_tuple_type(self) -> None:
        """Test adding message types as tuple to the registry."""
        registry = MessageRegistry()

        # Test with tuple of types
        tuple_types = (DummyMessage, OtherDummyMessage)
        registry.add(tuple_types, "TestConsumer")

        # Both message types should be registered
        assert DummyMessage in registry.messages
        assert OtherDummyMessage in registry.messages

        assert registry.messages[DummyMessage] == "#/components/messages/dummy_message"
        assert (
            registry.messages[OtherDummyMessage]
            == "#/components/messages/other_dummy_message"
        )

        # Both should be in the consumer messages
        assert DummyMessage in registry.consumer_messages["TestConsumer"]
        assert OtherDummyMessage in registry.consumer_messages["TestConsumer"]
