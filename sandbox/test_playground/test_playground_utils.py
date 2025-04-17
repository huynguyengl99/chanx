from unittest import mock

from django.test import TestCase

from chanx.messages.base import BaseIncomingMessage
from chanx.playground.utils import (
    get_message_examples,
)
from pydantic import BaseModel


class TestPlaygroundUtilsEdgeCases(TestCase):
    """Tests for edge cases and exception handling in WebSocket playground utilities."""

    def test_get_message_examples_non_union_type(self):
        """Test get_message_examples with a non-union message type."""

        # Create a simple message type
        class SimpleMessage(BaseModel):
            field: str = "test"

        # Create a mock that will return SimpleMessage for the message field
        with (
            mock.patch(
                "chanx.playground.utils.get_type_hints",
                return_value={"message": SimpleMessage},
            ),
            mock.patch("chanx.playground.utils.get_origin", return_value=None),
            mock.patch("chanx.playground.utils._create_example") as mock_create_example,
        ):
            # Set up the mock to return a sample example
            mock_create_example.return_value = {
                "name": "SimpleMessage",
                "description": "Simple message",
                "example": {"field": "test"},
            }

            # Call the function
            result = get_message_examples(mock.Mock(spec=BaseIncomingMessage))

            # Verify we got a single example
            assert len(result) == 1
            assert result[0]["name"] == "SimpleMessage"
            assert result[0]["example"]["field"] == "test"

            # Verify _create_example was called with SimpleMessage
            mock_create_example.assert_called_once_with(SimpleMessage)
