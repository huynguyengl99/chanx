# pyright: reportUnusedClass=false

from typing import Any, Literal
from unittest import TestCase

import pytest

# Import the classes we're testing
from chanx.messages.base import (
    BaseMessage,
)


class TestBaseMessage(TestCase):
    """Test cases for the BaseMessage class."""

    def test_valid_concrete_message(self) -> None:
        """Test that a valid concrete message subclass can be defined."""

        class ValidMessage(BaseMessage):
            action: Literal["valid_action"]

        # This should not raise any exceptions
        message = ValidMessage(action="valid_action", payload=None)
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

        parent = ParentMessage(
            action="parent_action", parent_field="value", payload=None
        )
        child = ChildMessage(
            action="child_action", parent_field="value", child_field=42, payload=None
        )

        assert parent.action == "parent_action"
        assert parent.parent_field == "value"

        assert child.action == "child_action"
        assert child.parent_field == "value"
        assert child.child_field == 42

    def test_abc_base_class_skipped(self) -> None:
        """Test that ABC base classes are skipped during validation."""
        import abc

        class AbstractMessage(BaseMessage, abc.ABC):
            # ABC classes should not be validated - covers line 64
            pass

        # Should not raise TypeError for missing action field
        # because it's an ABC base class
        assert abc.ABC in AbstractMessage.__bases__
