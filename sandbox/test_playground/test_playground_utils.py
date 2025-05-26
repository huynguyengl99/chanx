from typing import Literal
from unittest import mock

from django.test import TestCase

from chanx.messages.base import BaseMessage
from chanx.playground.utils import (
    get_message_examples,
)


class TestPlaygroundUtilsEdgeCases(TestCase):
    """Tests for edge cases and exception handling in WebSocket playground utilities."""

    def test_get_message_examples_none_type(self) -> None:
        # Call the function with None
        result = get_message_examples(None)

        # Verify we got an empty list
        self.assertEqual(result, [])

    def test_get_message_examples_exception_handling(self) -> None:
        # Create a mock that will raise an exception during processing
        mock_message_type = mock.Mock(spec=BaseMessage)

        # Force an exception to be raised during processing
        with mock.patch(
            "chanx.playground.utils.get_origin",
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
        SingleTypeMessage = TestMessage

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

            with mock.patch("chanx.playground.utils.get_origin", return_value=None):
                result = get_message_examples(SingleTypeMessage)

                # We should get a single example
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["name"], "TestMessage")
