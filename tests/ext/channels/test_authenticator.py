"""
Tests for auth.py module.

This module tests the ChanxSerializer and ChanxAuthView classes
to ensure they work as expected for authentication.
"""

import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

import pytest
from asgiref.sync import sync_to_async
from chanx.ext.channels.authenticator import (
    ChanxAuthView,
    ChanxSerializer,
    DjangoAuthenticator,
)
from chanx.type_defs import SendMessageFn


class TestChanxSerializer:
    """Tests for the ChanxSerializer class."""

    def test_serializer_fields(self) -> None:
        """Test that the serializer has expected fields."""
        serializer = ChanxSerializer()
        assert "detail" in serializer.fields
        assert serializer.fields["detail"].write_only is True
        assert serializer.fields["detail"].required is False


class TestChanxAuthView:
    """Tests for the ChanxAuthView class."""

    def setup_method(self) -> None:
        """Set up test environment before each test method."""
        self.view = ChanxAuthView()
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.view.request = Request(self.request)  # pyright: ignore[reportCallIssue]
        self.view.kwargs = {}

    def test_get_response_without_detail(self) -> None:
        """Test get_response when detail is None and no lookup param."""
        response = self.view.get_response(self.view.request)
        assert isinstance(response, Response)
        assert response.data == {"detail": "ok"}
        assert response.status_code == 200

    def test_get_response_without_lookup_parameter(self) -> None:
        """Test get_response when no lookup parameter is present."""
        self.view.kwargs = {}

        # No need to mock get_object as it shouldn't be called
        self.view.get_object = MagicMock()  # type: ignore[method-assign]

        response = self.view.get_response(self.view.request)
        assert not self.view.get_object.called
        assert response.data == {"detail": "ok"}

    def test_http_methods(self) -> None:
        """Test that all HTTP methods return the response from get_response."""
        methods = ["get", "post", "put", "patch", "delete"]

        for method_name in methods:
            method = getattr(self.view, method_name)

            with patch.object(self.view, "get_response") as mock_get_response:
                mock_get_response.return_value = Response({"test": "value"})

                response = method(self.view.request)

                assert mock_get_response.called
                assert response == mock_get_response.return_value


@pytest.mark.parametrize("method_name", ["get", "post", "put", "patch", "delete"])
def test_http_method_calls_get_response(method_name: str) -> None:
    """Test that each HTTP method calls get_response correctly."""
    view = ChanxAuthView()
    request_factory = RequestFactory()

    # Create a request for the specific method
    request_method = getattr(request_factory, method_name)
    request = request_method("/")
    drf_request = Request(request)  # pyright: ignore[reportCallIssue]

    # Set up the view
    view.request = drf_request
    view.kwargs = {}

    with patch.object(view, "get_response") as mock_get_response:
        mock_get_response.return_value = Response({"test": "response"})

        # Call the method
        method = getattr(view, method_name)
        response = method(drf_request)

        # Verify get_response was called and its return value was returned
        mock_get_response.assert_called_once_with(drf_request)
        assert response == mock_get_response.return_value


class TestDjangoAuthenticator(TestCase):
    """Tests for the DjangoAuthenticator class."""

    def setUp(self) -> None:
        """Set up test environment before each test method."""
        self.factory = RequestFactory()
        self.send_message_mock = AsyncMock()
        self.authenticator = DjangoAuthenticator(self.send_message_mock)
        self.default_scope: dict[str, Any] = {
            "type": "websocket",
            "path": "/ws/test/",
            "headers": [
                (b"host", b"localhost:8000"),
                (b"x-request-id", b"test-request-id"),
            ],
            "query_string": b"",
            "client": ("127.0.0.1", 43210),
            "url_route": {
                "args": [],
                "kwargs": {},
            },
        }

    def _create_scope_with_pk(self, pk: int) -> dict[str, Any]:
        return {
            "type": "websocket",
            "path": "/ws/chat/1/",
            "headers": [(b"host", b"localhost:8000")],
            "query_string": b"",
            "client": ("127.0.0.1", 43210),
            "url_route": {
                "args": [],
                "kwargs": {"pk": str(pk)},
            },
        }

    def test_validate_configuration_check_has_object_permission_method(self) -> None:
        """Test validate_configuration checks for has_object_permission method."""

        self.authenticator.permission_classes = [IsAuthenticated]
        self.authenticator.queryset = True
        with warnings.catch_warnings(record=True) as w:
            self.authenticator.validate_configuration()
            assert len(w) == 0

        self.authenticator.permission_classes = None
        self.authenticator.queryset = True

        with warnings.catch_warnings(record=True) as w:
            self.authenticator.validate_configuration()
            assert len(w) == 0

        # Create permission class with has_object_permission defined in parent class
        class BaseObjectPermission(IsAuthenticated):
            def has_object_permission(
                self, request: Request, view: APIView, obj: Any
            ) -> bool:
                return True

        class ChildPermission(BaseObjectPermission):
            # Inherits has_object_permission from parent
            pass

        # Create permission class with has_object_permission defined in this class
        class DirectObjectPermission(IsAuthenticated):
            def has_object_permission(
                self, request: Request, view: APIView, obj: Any
            ) -> bool:
                return True

        self.authenticator.permission_classes = [ChildPermission]
        self.authenticator.queryset = True

        with warnings.catch_warnings(record=True) as w:
            self.authenticator.validate_configuration()
            assert len(w) == 1
            assert "may require object access" in str(w[0].message)

        self.authenticator.permission_classes = [DirectObjectPermission]
        with warnings.catch_warnings(record=True) as w:
            self.authenticator.validate_configuration()
            assert len(w) == 1
            assert "may require object access" in str(w[0].message)

        # Will not warn for and operand
        self.authenticator.permission_classes = [
            DirectObjectPermission & IsAuthenticated
        ]
        with warnings.catch_warnings(record=True) as w:
            self.authenticator.validate_configuration()
            assert len(w) == 0

    def test_validate_scope_configuration_no_lookup(self) -> None:
        """Test _validate_scope_configuration with no lookup parameters."""
        # Create a scope with no URL lookup parameters
        scope: dict[str, Any] = {"url_route": {"kwargs": {}}}

        # Should not raise any exceptions
        self.authenticator._validate_scope_configuration(scope)

    def test_validate_scope_configuration_with_lookup_no_queryset(self) -> None:
        """Test _validate_scope_configuration with lookup but no queryset raises error."""
        # Create a scope with a URL lookup parameter
        scope = {"url_route": {"kwargs": {"pk": "1"}}}

        # Should raise ValueError
        with pytest.raises(ValueError) as context:
            self.authenticator._validate_scope_configuration(scope)

        assert "Object retrieval requires a queryset" in str(context.value)

    @pytest.mark.asyncio
    async def test_authenticate_no_permission(self) -> None:
        """Test that authentication works."""
        result = await self.authenticator.authenticate(self.default_scope)
        assert result

    @pytest.mark.asyncio
    async def test_authenticate_failed_permission(self) -> None:
        class IsAuthenticatedCWebsocketAuthenticator(DjangoAuthenticator):
            permission_classes = (IsAuthenticated,)

        authenticator = IsAuthenticatedCWebsocketAuthenticator(AsyncMock())

        result = await authenticator.authenticate(self.default_scope)
        assert not result

    @pytest.mark.asyncio
    async def test_authenticate_exception(self) -> None:
        """Test authenticate handles exceptions gracefully."""
        # Configure authenticator that will raise an exception
        with patch.object(self.authenticator, "_perform_dispatch") as mock_dispatch:
            mock_dispatch.side_effect = Exception("Test exception")

            # Authenticate
            result = await self.authenticator.authenticate(self.default_scope)

            # Assert the result is a generic error
            assert not result

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_authenticate_with_object(self) -> None:
        """Test authenticate with object retrieval from URL parameter."""
        # Use Django's built-in User model for simplicity
        user = await sync_to_async(User.objects.create)(username="testuser")

        # Configure authenticator with User queryset
        class UserAuthenticator(DjangoAuthenticator):
            def __init__(self, send_message: SendMessageFn) -> None:
                super().__init__(send_message)
                self.queryset = User.objects.all()

        authenticator = UserAuthenticator(AsyncMock())

        # Update the scope with the real user id
        scope_with_real_pk = self._create_scope_with_pk(user.pk)

        result = await authenticator.authenticate(scope_with_real_pk)

        # Verify object was included in result
        assert result
        assert authenticator.obj == user
