from typing import Literal
from unittest import mock

from django.test import TestCase

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.playground.utils import (
    get_message_examples,
)
from pydantic import BaseModel


class TestPlaygroundUtilsEdgeCases(TestCase):
    """Tests for edge cases and exception handling in WebSocket playground utilities."""

    def test_get_message_examples_non_union_type(self) -> None:
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
            result = get_message_examples(
                mock.Mock(spec=BaseIncomingMessage)  # pyright: ignore
            )
            # Verify we got a single example
            assert len(result) == 1
            assert result[0]["name"] == "SimpleMessage"
            assert result[0]["example"]["field"] == "test"

            # Verify _create_example was called with SimpleMessage
            mock_create_example.assert_called_once_with(SimpleMessage)

    def test_get_message_examples_none_type(self) -> None:
        # Call the function with None
        result = get_message_examples(None)

        # Verify we got an empty list
        self.assertEqual(result, [])

    def test_get_message_examples_no_message_field(self) -> None:
        # Create a mock message type that will fail to have the 'message' field
        mock_message_type = mock.Mock(spec=BaseIncomingMessage)

        # Mock get_type_hints to return empty dict (no message field)
        with mock.patch("chanx.playground.utils.get_type_hints", return_value={}):
            result = get_message_examples(mock_message_type)  # pyright: ignore

            # Should return empty list when no message field is found
            self.assertEqual(result, [])

    def test_get_message_examples_exception_handling(self) -> None:
        # Create a mock that will raise an exception during processing
        mock_message_type = mock.Mock(spec=BaseIncomingMessage)

        # Force an exception to be raised during processing
        with mock.patch(
            "chanx.playground.utils.get_type_hints",
            side_effect=Exception("Test exception"),
        ):
            # Function should return empty list when exception occurs
            result = get_message_examples(mock_message_type)  # pyright: ignore
            self.assertEqual(result, [])

    def test_create_example_with_real_types(self) -> None:
        # Create concrete message types
        class TestMessage(BaseMessage):
            action: Literal["test_action"]
            data: str = "test data"

        # Create a container message that is not a union
        class SingleTypeMessage(BaseIncomingMessage):
            message: TestMessage

        # Mock ModelFactory to return a predictable result
        with mock.patch("chanx.playground.utils.ModelFactory") as mock_factory:
            mock_factory_instance = mock.MagicMock()
            mock_factory.create_factory.return_value = mock_factory_instance
            mock_model = mock.MagicMock()
            mock_model.model_dump.return_value = {
                "action": "test_action",
                "data": "test data",
            }
            mock_factory_instance.build.return_value = mock_model

            # Use type hints patching to simulate a non-union message field
            with mock.patch(
                "chanx.playground.utils.get_type_hints",
                return_value={"message": TestMessage},
            ):
                # Ensure get_origin returns None to indicate it's not a Union
                with mock.patch("chanx.playground.utils.get_origin", return_value=None):
                    result = get_message_examples(SingleTypeMessage)

                    # We should get a single example
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0]["name"], "TestMessage")
