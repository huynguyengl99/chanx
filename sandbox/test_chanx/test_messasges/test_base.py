from typing import Any, ClassVar, Literal

from django.test import SimpleTestCase

import pytest

# Import the classes we're testing
from chanx.messages.base import (
    BaseGroupMessage,
    BaseIncomingMessage,
    BaseMessage,
    BaseOutgoingGroupMessage,
    MessageContainerMixin,
)
from pydantic import Field


class TestBaseMessage(SimpleTestCase):
    """Test cases for the BaseMessage class."""

    def test_valid_concrete_message(self) -> None:
        """Test that a valid concrete message subclass can be defined."""

        class ValidMessage(BaseMessage):
            action: Literal["valid_action"]

        # This should not raise any exceptions
        message = ValidMessage(action="valid_action")
        assert message.action == "valid_action"
        assert message.payload is None

    def test_valid_concrete_message_with_payload(self) -> None:
        """Test that a valid message with payload can be defined."""

        class ValidMessageWithPayload(BaseMessage):
            action: Literal["with_payload"]
            payload: dict[str, Any]

        message = ValidMessageWithPayload(
            action="with_payload", payload={"key": "value"}
        )
        assert message.action == "with_payload"
        assert message.payload == {"key": "value"}

    def test_missing_action_field(self) -> None:
        """Test that a TypeError is raised when 'action' field is missing."""
        with pytest.raises(TypeError, match=r"must define an 'action' field"):
            # Missing 'action' field
            class InvalidMessage(BaseMessage):
                other_field: str

    def test_non_literal_action_field(self) -> None:
        """Test that a TypeError is raised when 'action' is not a Literal."""
        with pytest.raises(
            TypeError, match=r"requires the field 'action' to be a `Literal` type"
        ):
            # 'action' is not a Literal type
            class InvalidMessage(BaseMessage):
                action: str

    def test_inheritance(self) -> None:
        """Test that inheritance works correctly for BaseMessage."""

        class ParentMessage(BaseMessage):
            action: Literal["parent_action"]
            parent_field: str

        class ChildMessage(ParentMessage):
            action: Literal["child_action"]  # type: ignore[assignment]
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


class GroupMessage1(BaseGroupMessage):
    action: Literal["group_action1"]
    group_field1: str


class GroupMessage2(BaseGroupMessage):
    action: Literal["group_action2"]
    group_field2: int


class TestBaseIncomingMessage(SimpleTestCase):
    """Test cases for the BaseIncomingMessage class."""

    def test_valid_incoming_message(self) -> None:
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

    def test_direct_basemessage_field(self) -> None:
        """Test that a direct BaseMessage field is allowed."""

        class ValidDirectMessage(BaseIncomingMessage):
            message: Message1

        message = Message1(action="action1", field1="test")
        incoming = ValidDirectMessage(message=message)
        assert incoming.message.action == "action1"
        assert incoming.message.field1 == "test"

    def test_missing_message_field(self) -> None:
        """Test that TypeError is raised when 'message' field is missing."""
        with pytest.raises(TypeError, match=r"must define a 'message' field"):

            class InvalidIncoming(BaseIncomingMessage):
                wrong_field: str

    def test_non_basemessage_in_union(self) -> None:
        """Test that TypeError is raised when union contains non-BaseMessage types."""
        with pytest.raises(TypeError, match=r"must be subclasses of BaseMessage"):

            class InvalidUnionIncoming(BaseIncomingMessage):
                message: Message1 | str  # type: ignore[assignment]  # str is not a BaseMessage, testing

    def test_non_union_non_basemessage(self) -> None:
        """Test that TypeError is raised when 'message' is not a BaseMessage or union."""
        with pytest.raises(
            TypeError, match=r"must be BaseMessage or a union of BaseMessage subclasses"
        ):

            class InvalidTypeIncoming(BaseIncomingMessage):
                message: str  # type: ignore[assignment]  # str is not a BaseMessage or union of BaseMessages

    def test_json_serialization(self) -> None:
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

    def test_explicit_discriminator(self) -> None:
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


class TestBaseOutgoingGroupMessage(SimpleTestCase):
    """Test cases for the BaseOutgoingGroupMessage class."""

    def test_valid_outgoing_group_message(self) -> None:
        """Test that a valid outgoing group message can be defined with a union."""

        class ValidOutgoingMessage(BaseOutgoingGroupMessage):
            group_message: GroupMessage1 | GroupMessage2

        # Create instances of both message types
        message1 = GroupMessage1(action="group_action1", group_field1="test")
        message2 = GroupMessage2(action="group_action2", group_field2=123)

        # Validate that both work in the outgoing message
        outgoing1 = ValidOutgoingMessage(group_message=message1)
        outgoing2 = ValidOutgoingMessage(group_message=message2)

        assert outgoing1.group_message.action == "group_action1"
        assert outgoing1.group_message.group_field1 == "test"
        assert outgoing2.group_message.action == "group_action2"
        assert outgoing2.group_message.group_field2 == 123

    def test_direct_basegroupmessage_field(self) -> None:
        """Test that a direct BaseGroupMessage field is allowed."""

        class ValidDirectMessage(BaseOutgoingGroupMessage):
            group_message: GroupMessage1

        message = GroupMessage1(action="group_action1", group_field1="test")
        outgoing = ValidDirectMessage(group_message=message)
        assert outgoing.group_message.action == "group_action1"
        assert outgoing.group_message.group_field1 == "test"

    def test_missing_group_message_field(self) -> None:
        """Test that TypeError is raised when 'group_message' field is missing."""
        with pytest.raises(TypeError, match=r"must define a 'group_message' field"):

            class InvalidOutgoing(BaseOutgoingGroupMessage):
                wrong_field: str

    def test_non_basegroupmessage_in_union(self) -> None:
        """Test that TypeError is raised when union contains non-BaseGroupMessage types."""
        with pytest.raises(TypeError, match=r"must be subclasses of BaseGroupMessage"):

            class InvalidUnionOutgoing(BaseOutgoingGroupMessage):
                group_message: GroupMessage1 | str  # type: ignore[assignment]  # str is not a BaseGroupMessage

    def test_non_union_non_basegroupmessage(self) -> None:
        """Test that TypeError is raised when 'group_message' is not a BaseGroupMessage or union."""
        with pytest.raises(
            TypeError,
            match=r"must be BaseGroupMessage or a union of BaseGroupMessage subclasses",
        ):

            class InvalidTypeOutgoing(BaseOutgoingGroupMessage):
                group_message: str  # type: ignore[assignment]  # str is not a BaseGroupMessage or union of BaseGroupMessages

    def test_json_serialization(self) -> None:
        """Test that group messages can be properly serialized to JSON with type discrimination."""

        class OutgoingMessageTest(BaseOutgoingGroupMessage):
            group_message: GroupMessage1 | GroupMessage2

        # Create test messages
        message1 = GroupMessage1(action="group_action1", group_field1="value1")
        outgoing1 = OutgoingMessageTest(group_message=message1)

        # Serialize to JSON
        json_data = outgoing1.model_dump_json()

        # Deserialize and validate
        outgoing_restored = OutgoingMessageTest.model_validate_json(json_data)
        assert outgoing_restored.group_message.action == "group_action1"
        assert outgoing_restored.group_message.group_field1 == "value1"
        assert isinstance(outgoing_restored.group_message, GroupMessage1)

    def test_explicit_discriminator(self) -> None:
        """Test with an explicitly defined discriminator."""

        class ExplicitDiscriminatorMessage(BaseOutgoingGroupMessage):
            group_message: GroupMessage1 | GroupMessage2 = Field(discriminator="action")

        # Create test message
        message2 = GroupMessage2(action="group_action2", group_field2=42)
        outgoing = ExplicitDiscriminatorMessage(group_message=message2)

        # Validate parsing works with the discriminator
        json_data = outgoing.model_dump_json()
        outgoing_restored = ExplicitDiscriminatorMessage.model_validate_json(json_data)
        assert outgoing_restored.group_message.action == "group_action2"
        assert outgoing_restored.group_message.group_field2 == 42
        assert isinstance(outgoing_restored.group_message, GroupMessage2)


class TestMessageContainerMixin(SimpleTestCase):
    """Test cases for the MessageContainerMixin class."""

    def test_custom_message_container(self) -> None:
        """Test creating a custom message container class with the mixin."""

        class CustomMessage(BaseMessage):
            action: Literal["custom_action"]
            data: str

        class CustomContainer(MessageContainerMixin):
            _message_field_name: ClassVar[str] = "custom_field"
            _message_base_class: ClassVar[type[BaseMessage]] = BaseMessage

            custom_field: CustomMessage

        # Create a test message
        message = CustomMessage(action="custom_action", data="test_data")
        container = CustomContainer(custom_field=message)

        assert container.custom_field.action == "custom_action"
        assert container.custom_field.data == "test_data"
        assert isinstance(container.custom_field, CustomMessage)

    def test_custom_container_with_union(self) -> None:
        """Test creating a custom container with a union of message types."""

        class CustomMessage1(BaseMessage):
            action: Literal["custom1"]
            field1: str

        class CustomMessage2(BaseMessage):
            action: Literal["custom2"]
            field2: int

        class CustomUnionContainer(MessageContainerMixin):
            _message_field_name: ClassVar[str] = "custom_field"
            _message_base_class: ClassVar[type[BaseMessage]] = BaseMessage

            custom_field: CustomMessage1 | CustomMessage2

        # Create test messages
        message1 = CustomMessage1(action="custom1", field1="test")
        message2 = CustomMessage2(action="custom2", field2=42)

        # Validate both message types work
        container1 = CustomUnionContainer(custom_field=message1)
        container2 = CustomUnionContainer(custom_field=message2)

        assert container1.custom_field.action == "custom1"
        assert container1.custom_field.field1 == "test"
        assert container2.custom_field.action == "custom2"
        assert container2.custom_field.field2 == 42

    def test_missing_required_class_var(self) -> None:
        """Test that error is raised when required class variables are missing."""

        with pytest.raises(AttributeError):

            class MissingFieldName(MessageContainerMixin):
                # Missing _message_field_name
                _message_base_class: ClassVar[type[BaseMessage]] = BaseMessage

                message: Message1

        with pytest.raises(AttributeError):

            class MissingBaseClass(MessageContainerMixin):
                _message_field_name: ClassVar[str] = "message"
                # Missing _message_base_class

                message: Message1

    def test_wrong_field_name(self) -> None:
        """Test that error is raised when field name doesn't match _message_field_name."""

        with pytest.raises(TypeError, match=r"must define a 'custom_field' field"):

            class WrongFieldName(MessageContainerMixin):
                _message_field_name: ClassVar[str] = "custom_field"
                _message_base_class: ClassVar[type[BaseMessage]] = BaseMessage

                message: Message1  # Field name doesn't match _message_field_name
