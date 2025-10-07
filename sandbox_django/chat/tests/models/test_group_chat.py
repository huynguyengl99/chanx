from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from chat.factories.group_chat import GroupChatFactory


class GroupChatModelTestCase(TestCase):
    """Test cases for GroupChat model"""

    def test_group_chat_string_representation(self) -> None:
        """Test __str__ method returns title"""
        group_chat = GroupChatFactory.create(title="My Chat Room")
        assert str(group_chat) == "My Chat Room"

    def test_update_last_activity(self) -> None:
        """Test update_last_activity method updates timestamp"""
        group_chat = GroupChatFactory.create()
        original_updated_at = group_chat.updated_at

        # Mock timezone.now() to return a specific time
        mock_time = timezone.now() + timedelta(hours=1)

        with patch("django.utils.timezone.now", return_value=mock_time):
            group_chat.update_last_activity()

        # Refresh from database
        group_chat.refresh_from_db()

        # Should be updated to the mocked time
        assert group_chat.updated_at == mock_time
        assert group_chat.updated_at > original_updated_at
