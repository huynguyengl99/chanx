from typing import Any, Literal

from django.test import SimpleTestCase

import pytest

# Import the classes we're testing
from chanx.messages.base import BaseIncomingMessage, BaseMessage
from pydantic import Field


class TestBaseMessage(SimpleTestCase):
    """Test cases for the BaseMessage class."""

    def test_valid_concrete_message(self):
        """Test that a valid concrete message subclass can be defined."""

        class ValidMessage(BaseMessage):
            action: Literal["valid_action"]

        # This should not raise any exceptions
        message = ValidMessage(action="valid_action")
        assert message.action == "valid_action"
        assert message.payload is None

    def test_valid_concrete_message_with_payload(self):
        """Test that a valid message with payload can be defined."""

        class ValidMessageWithPayload(BaseMessage):
            action: Literal["with_payload"]
            payload: dict[str, Any]

        message = ValidMessageWithPayload(
            action="with_payload", payload={"key": "value"}
        )
        assert message.action == "with_payload"
        assert message.payload == {"key": "value"}

    def test_missing_action_field(self):
        """Test that a TypeError is raised when 'action' field is missing."""
        with pytest.raises(TypeError, match=r"must define an 'action' field"):
            # Missing 'action' field
            class InvalidMessage(BaseMessage):
                other_field: str

    def test_non_literal_action_field(self):
        """Test that a TypeError is raised when 'action' is not a Literal."""
        with pytest.raises(
            TypeError, match=r"requires the field 'action' to be a `Literal` type"
        ):
            # 'action' is not a Literal type
            class InvalidMessage(BaseMessage):
                action: str

    def test_inheritance(self):
        """Test that inheritance works correctly for BaseMessage."""

        class ParentMessage(BaseMessage):
            action: Literal["parent_action"]
            parent_field: str

        class ChildMessage(ParentMessage):
            action: Literal["child_action"]
            child_field: int

        parent = ParentMessage(action="parent_action", parent_field="value")
        child = ChildMessage(
            action="child_action", parent_field="value", child_field=42
        )

        assert parent.action == "parent_action"
        assert parent.parent_field == "value"

        assert child.action == "child_action"
        assert child.parent_field == "value"
        assert child.child_field == 42


class Message1(BaseMessage):
    action: Literal["action1"]
    field1: str


class Message2(BaseMessage):
    action: Literal["action2"]
    field2: int


class TestBaseIncomingMessage(SimpleTestCase):
    """Test cases for the BaseIncomingMessage class."""

    def test_valid_incoming_message(self):
        """Test that a valid incoming message can be defined with a union."""

        class ValidIncomingMessage(BaseIncomingMessage):
            message: Message1 | Message2

        # Create instances of both message types
        message1 = Message1(action="action1", field1="test")
        message2 = Message2(action="action2", field2=123)

        # Validate that both work in the incoming message
        incoming1 = ValidIncomingMessage(message=message1)
        incoming2 = ValidIncomingMessage(message=message2)

        assert incoming1.message.action == "action1"
        assert incoming1.message.field1 == "test"
        assert incoming2.message.action == "action2"
        assert incoming2.message.field2 == 123

    def test_direct_basemessage_field(self):
        """Test that a direct BaseMessage field is allowed."""

        class ValidDirectMessage(BaseIncomingMessage):
            message: Message1

        message = Message1(action="action1", field1="test")
        incoming = ValidDirectMessage(message=message)
        assert incoming.message.action == "action1"
        assert incoming.message.field1 == "test"

    def test_missing_message_field(self):
        """Test that TypeError is raised when 'message' field is missing."""
        with pytest.raises(TypeError, match=r"must define a 'message' field"):

            class InvalidIncoming(BaseIncomingMessage):
                wrong_field: str

    def test_non_basemessage_in_union(self):
        """Test that TypeError is raised when union contains non-BaseMessage types."""
        with pytest.raises(TypeError, match=r"must be subclasses of BaseMessage"):

            class InvalidUnionIncoming(BaseIncomingMessage):
                message: Message1 | str  # str is not a BaseMessage

    def test_non_union_non_basemessage(self):
        """Test that TypeError is raised when 'message' is not a BaseMessage or union."""
        with pytest.raises(
            TypeError, match=r"must be BaseMessage or a union of BaseMessage subclasses"
        ):

            class InvalidTypeIncoming(BaseIncomingMessage):
                message: str  # str is not a BaseMessage or union of BaseMessages

    def test_json_serialization(self):
        """Test that messages can be properly serialized to JSON with type discrimination."""

        class IncomingMessageTest(BaseIncomingMessage):
            message: Message1 | Message2

        # Create test messages
        message1 = Message1(action="action1", field1="value1")
        incoming1 = IncomingMessageTest(message=message1)

        # Serialize to JSON
        json_data = incoming1.model_dump_json()

        # Deserialize and validate
        incoming_restored = IncomingMessageTest.model_validate_json(json_data)
        assert incoming_restored.message.action == "action1"
        assert incoming_restored.message.field1 == "value1"
        assert isinstance(incoming_restored.message, Message1)

    def test_explicit_discriminator(self):
        """Test with an explicitly defined discriminator."""

        class ExplicitDiscriminatorMessage(BaseIncomingMessage):
            message: Message1 | Message2 = Field(discriminator="action")

        # Create test message
        message2 = Message2(action="action2", field2=42)
        incoming = ExplicitDiscriminatorMessage(message=message2)

        # Validate parsing works with the discriminator
        json_data = incoming.model_dump_json()
        incoming_restored = ExplicitDiscriminatorMessage.model_validate_json(json_data)
        assert incoming_restored.message.action == "action2"
        assert incoming_restored.message.field2 == 42
        assert isinstance(incoming_restored.message, Message2)
