from django.test import TestCase

from accounts.factories.user import UserFactory

from chat.factories.chat_member import ChatMemberFactory
from chat.factories.group_chat import GroupChatFactory
from chat.models import ChatMessage


class ChatMessageModelTestCase(TestCase):
    """Test cases for ChatMessage model"""

    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.group_chat = GroupChatFactory.create()
        self.chat_member = ChatMemberFactory.create(
            user=self.user, group_chat=self.group_chat
        )

    def test_save_new_message_updates_group_chat_activity(self) -> None:
        """Test that saving a new message updates group chat's last activity"""
        original_updated_at = self.group_chat.updated_at

        # Create a new message
        message = ChatMessage.objects.create(
            group_chat=self.group_chat, sender=self.chat_member, content="Test message"
        )

        # Refresh group chat from database
        self.group_chat.refresh_from_db()

        # The group chat's updated_at should be newer
        assert self.group_chat.updated_at > original_updated_at
        assert message.content == "Test message"

    def test_save_existing_message_does_not_update_group_chat_activity(self) -> None:
        """Test that updating existing message doesn't update group chat activity"""
        # Create a message first
        message = ChatMessage.objects.create(
            group_chat=self.group_chat,
            sender=self.chat_member,
            content="Original content",
        )

        # Record the group chat's updated time
        self.group_chat.refresh_from_db()
        original_updated_at = self.group_chat.updated_at

        # Update the message (not new anymore)
        message.content = "Updated content"
        message.save()

        # Group chat updated_at should remain the same
        self.group_chat.refresh_from_db()
        assert self.group_chat.updated_at == original_updated_at
