from unittest.mock import Mock, patch

from django.test import TestCase

from accounts.factories.user import UserFactory
from accounts.models import User

from assistants.constants import TRUNCATED_TITLE_LENGTH
from assistants.models import AssistantConversation, AssistantMessage


class AssistantConversationModelTest(TestCase):
    """Test cases for AssistantConversation model."""

    user: User

    def setUp(self) -> None:
        self.user = UserFactory.create()

    def test_str_representation_with_user_and_title(self) -> None:
        """Test string representation with user and title."""
        conversation = AssistantConversation.objects.create(
            user=self.user, title="Test Conversation"
        )
        expected = (
            f"Conversation {conversation.id} - Test Conversation ({self.user.email})"
        )
        assert str(conversation) == expected

    def test_str_representation_with_user_no_title(self) -> None:
        """Test string representation with user but no title."""
        conversation = AssistantConversation.objects.create(user=self.user)
        expected = f"Conversation {conversation.id} - Untitled ({self.user.email})"
        assert str(conversation) == expected

    def test_str_representation_anonymous_with_title(self) -> None:
        """Test string representation for anonymous user with title."""
        conversation = AssistantConversation.objects.create(
            user=None, title="Anonymous Chat"
        )
        expected = f"Conversation {conversation.id} - Anonymous Chat (anonymous)"
        assert str(conversation) == expected

    def test_str_representation_anonymous_no_title(self) -> None:
        """Test string representation for anonymous user without title."""
        conversation = AssistantConversation.objects.create(user=None)
        expected = f"Conversation {conversation.id} - Untitled (anonymous)"
        assert str(conversation) == expected

    @patch("assistants.tasks.ai_service_tasks.task_generate_conversation_title")
    def test_generate_title_from_first_message_success(
        self, mock_generate_title: Mock
    ) -> None:
        """Test successful title generation from first message."""
        mock_generate_title.return_value = "Generated Title"

        conversation = AssistantConversation.objects.create(user=self.user)
        AssistantMessage.objects.create(
            conversation=conversation,
            content="Hello, this is my first message",
            message_type=AssistantMessage.MessageType.USER,
        )

        conversation.generate_title_from_first_message()

        mock_generate_title.assert_called_once_with("Hello, this is my first message")
        conversation.refresh_from_db()
        assert conversation.title == "Generated Title"

    @patch("assistants.tasks.ai_service_tasks.task_generate_conversation_title")
    def test_generate_title_from_first_message_fallback_to_truncation(
        self, mock_generate_title: Mock
    ) -> None:
        """Test fallback to truncation when AI title generation fails."""
        mock_generate_title.side_effect = Exception("AI service error")

        long_message = "A" * (
            TRUNCATED_TITLE_LENGTH + 10
        )  # Create a message longer than truncation limit
        conversation = AssistantConversation.objects.create(user=self.user)
        AssistantMessage.objects.create(
            conversation=conversation,
            content=long_message,
            message_type=AssistantMessage.MessageType.USER,
        )

        conversation.generate_title_from_first_message()

        mock_generate_title.assert_called_once_with(long_message)
        conversation.refresh_from_db()
        expected_title = long_message[:TRUNCATED_TITLE_LENGTH] + "..."
        assert conversation.title == expected_title

    @patch("assistants.tasks.ai_service_tasks.task_generate_conversation_title")
    def test_generate_title_from_first_message_short_fallback(
        self, mock_generate_title: Mock
    ) -> None:
        """Test fallback with short message that doesn't need truncation."""
        mock_generate_title.side_effect = Exception("AI service error")

        short_message = "Short message"
        conversation = AssistantConversation.objects.create(user=self.user)
        AssistantMessage.objects.create(
            conversation=conversation,
            content=short_message,
            message_type=AssistantMessage.MessageType.USER,
        )

        conversation.generate_title_from_first_message()

        mock_generate_title.assert_called_once_with(short_message)
        conversation.refresh_from_db()
        assert conversation.title == short_message

    def test_generate_title_ignores_assistant_messages(self) -> None:
        """Test that title generation ignores assistant messages and finds first user message."""
        conversation = AssistantConversation.objects.create(user=self.user)

        # Create an assistant message first
        AssistantMessage.objects.create(
            conversation=conversation,
            content="I am an assistant message",
            message_type=AssistantMessage.MessageType.ASSISTANT,
        )

        # Create a user message
        AssistantMessage.objects.create(
            conversation=conversation,
            content="I am the first user message",
            message_type=AssistantMessage.MessageType.USER,
        )

        with patch(
            "assistants.tasks.ai_service_tasks.task_generate_conversation_title"
        ) as mock_generate:
            mock_generate.return_value = "User Message Title"
            conversation.generate_title_from_first_message()
            mock_generate.assert_called_once_with("I am the first user message")

    def test_ordering_by_updated_at_desc(self) -> None:
        """Test that conversations are ordered by updated_at in descending order."""
        # Create conversations with different update times
        conversation1 = AssistantConversation.objects.create(
            user=self.user, title="First"
        )
        conversation2 = AssistantConversation.objects.create(
            user=self.user, title="Second"
        )

        # Update conversation1 to make it more recent
        conversation1.title = "Updated First"
        conversation1.save()

        conversations = list(AssistantConversation.objects.all())
        assert conversations[0] == conversation1  # Most recently updated first
        assert conversations[1] == conversation2
