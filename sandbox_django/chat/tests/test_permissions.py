from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework import permissions
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from accounts.factories.user import UserFactory
from accounts.models import User

from chat.factories.chat_member import ChatMemberFactory
from chat.factories.group_chat import GroupChatFactory
from chat.models import ChatMember, GroupChat
from chat.permissions import (
    IsGroupChatMember,
    IsGroupChatMemberNested,
    ReadOnlyMemberOrOwner,
)


class ReadOnlyMemberOrOwnerTestCase(TestCase):
    """Test cases for ReadOnlyMemberOrOwner permission."""

    def setUp(self) -> None:
        self.permission = ReadOnlyMemberOrOwner()
        self.factory = APIRequestFactory()
        self.user: User = UserFactory.create()
        self.group_chat: GroupChat = GroupChatFactory.create()
        self.view = Mock(spec=APIView)

    def test_safe_methods_for_members(self) -> None:
        """Test safe methods for all member types."""
        ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)

        for method in permissions.SAFE_METHODS:
            request = getattr(self.factory, method.lower())("/test/")
            request.user = self.user
            result = self.permission.has_object_permission(
                request, self.view, self.group_chat
            )
            assert result is True

    def test_safe_methods_denied_for_non_members(self) -> None:
        """Test safe methods denied for non-members."""
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_object_permission(
            request, self.view, self.group_chat
        )
        assert result is False

    def test_unsafe_methods_only_for_owners(self) -> None:
        """Test unsafe methods only allowed for owners."""
        # Owner should be allowed
        ChatMemberFactory.create_owner(user=self.user, group_chat=self.group_chat)
        request = self.factory.post("/test/")
        request.user = self.user
        result = self.permission.has_object_permission(
            request, self.view, self.group_chat
        )
        assert result is True

        # Admin should be denied
        ChatMember.objects.filter(user=self.user).delete()
        ChatMemberFactory.create(
            user=self.user,
            group_chat=self.group_chat,
            chat_role=ChatMember.ChatMemberRole.ADMIN,
        )
        result = self.permission.has_object_permission(
            request, self.view, self.group_chat
        )
        assert result is False

        # Regular member should be denied
        ChatMember.objects.filter(user=self.user).delete()
        ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)
        result = self.permission.has_object_permission(
            request, self.view, self.group_chat
        )
        assert result is False


class IsGroupChatMemberTestCase(TestCase):
    """Test cases for IsGroupChatMember permission."""

    def setUp(self) -> None:
        self.permission = IsGroupChatMember()
        self.factory = APIRequestFactory()
        self.user: User = UserFactory.create()
        self.group_chat: GroupChat = GroupChatFactory.create()
        self.view = Mock(spec=APIView)
        self.view.kwargs = {"pk": self.group_chat.pk}

    def test_members_have_permission(self) -> None:
        """Test all member types have permission."""
        ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_permission(request, self.view)
        assert result is True

    def test_access_denied_cases(self) -> None:
        """Test various denied access cases."""
        # Non-member
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_permission(request, self.view)
        assert result is False

        # Unauthenticated user
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        result = self.permission.has_permission(request, self.view)
        assert result is False

        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        result = self.permission.has_permission(request, self.view)
        assert result is False

        # Missing pk
        self.view.kwargs = {}
        ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_permission(request, self.view)
        assert result is False


class IsGroupChatMemberNestedTestCase(TestCase):
    """Test cases for IsGroupChatMemberNested permission."""

    def setUp(self) -> None:
        self.permission = IsGroupChatMemberNested()
        self.factory = APIRequestFactory()
        self.user: User = UserFactory.create()
        self.group_chat: GroupChat = GroupChatFactory.create()
        self.view = Mock(spec=APIView)
        self.view.kwargs = {"group_chat_pk": self.group_chat.pk}

    def test_members_have_permission(self) -> None:
        """Test members have permission."""
        ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_permission(request, self.view)
        assert result is True

    def test_access_denied_cases(self) -> None:
        """Test various denied access cases."""
        # Non-member
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_permission(request, self.view)
        assert result is False

        # Unauthenticated user
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        result = self.permission.has_permission(request, self.view)
        assert result is False

        # Missing group_chat_pk
        self.view.kwargs = {}
        ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)
        request = self.factory.get("/test/")
        request.user = self.user
        result = self.permission.has_permission(request, self.view)
        assert result is False
