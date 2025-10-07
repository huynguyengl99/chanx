from django.test import TestCase

from accounts.factories.user import UserFactory

from assistants.models import AssistantConversation, AssistantMessage


class AssistantMessageModelTest(TestCase):
    """Test cases for AssistantMessage model."""

    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.conversation = AssistantConversation.objects.create(
            user=self.user, title="Test Conversation"
        )

    def test_str_representation_user_message(self) -> None:
        """Test string representation for user message."""
        message = AssistantMessage.objects.create(
            conversation=self.conversation,
            content="This is a test message from the user",
            message_type=AssistantMessage.MessageType.USER,
        )
        expected = "user: This is a test message from the user..."
        assert str(message) == expected

    def test_str_representation_assistant_message(self) -> None:
        """Test string representation for assistant message."""
        message = AssistantMessage.objects.create(
            conversation=self.conversation,
            content="This is a response from the assistant",
            message_type=AssistantMessage.MessageType.ASSISTANT,
        )
        expected = "assistant: This is a response from the assistant..."
        assert str(message) == expected

    def test_str_representation_long_content(self) -> None:
        """Test string representation truncates long content to 50 characters."""
        long_content = "A" * 100  # 100 characters
        message = AssistantMessage.objects.create(
            conversation=self.conversation,
            content=long_content,
            message_type=AssistantMessage.MessageType.USER,
        )
        expected = f"user: {'A' * 50}..."
        assert str(message) == expected

    def test_str_representation_short_content(self) -> None:
        """Test string representation with content shorter than 50 characters."""
        short_content = "Short message"
        message = AssistantMessage.objects.create(
            conversation=self.conversation,
            content=short_content,
            message_type=AssistantMessage.MessageType.USER,
        )
        expected = f"user: {short_content}..."
        assert str(message) == expected
