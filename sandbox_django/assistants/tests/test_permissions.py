from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from accounts.factories.user import UserFactory
from accounts.models import User

from assistants.factories import AssistantConversationFactory
from assistants.models import AssistantConversation
from assistants.permissions import ConversationOwner


class ConversationOwnerPermissionTestCase(TestCase):
    """Test cases for ConversationOwner permission."""

    def setUp(self) -> None:
        self.permission = ConversationOwner()
        self.factory = APIRequestFactory()
        self.user: User = UserFactory.create()
        self.other_user: User = UserFactory.create()
        self.view = Mock(spec=APIView)

    def test_has_object_permission_owner(self) -> None:
        """Test permission granted for conversation owner."""
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=self.user
        )

        request = self.factory.get("/test/")
        request.user = self.user

        result = self.permission.has_object_permission(request, self.view, conversation)
        assert result is True

    def test_has_object_permission_not_owner(self) -> None:
        """Test permission denied for non-owner."""
        conversation: AssistantConversation = AssistantConversationFactory.create(
            user=self.other_user
        )

        request = self.factory.get("/test/")
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.permission.has_object_permission(request, self.view, conversation)

    def test_has_object_permission_anonymous_conversation_any_user(self) -> None:
        """Test permission granted for anonymous conversation."""
        conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )

        request = self.factory.get("/test/")
        request.user = self.user

        result = self.permission.has_object_permission(request, self.view, conversation)
        assert result is True

    def test_has_object_permission_anonymous_conversation_no_user(self) -> None:
        """Test permission granted for anonymous conversation with no user."""
        conversation: AssistantConversation = (
            AssistantConversationFactory.create_anonymous()
        )

        request = self.factory.get("/test/")
        request.user = AnonymousUser()

        result = self.permission.has_object_permission(request, self.view, conversation)
        assert result is True
