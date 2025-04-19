"""
Tests for auth.py module.

This module tests the ChanxSerializer and ChanxAuthView classes
to ensure they work as expected for authentication.
"""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory
from rest_framework.request import Request
from rest_framework.response import Response

import pytest
from chanx.generic.authenticator import ChanxAuthView, ChanxSerializer


class TestChanxSerializer:
    """Tests for the ChanxSerializer class."""

    def test_serializer_fields(self):
        """Test that the serializer has expected fields."""
        serializer = ChanxSerializer()
        assert "detail" in serializer.fields
        assert serializer.fields["detail"].write_only is True
        assert serializer.fields["detail"].required is False


class TestChanxAuthView:
    """Tests for the ChanxAuthView class."""

    def setup_method(self):
        """Set up test environment before each test method."""
        self.view = ChanxAuthView()
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.view.request = Request(self.request)
        self.view.kwargs = {}

    def test_default_attributes(self):
        """Test default attributes of the view."""
        assert self.view.serializer_class == ChanxSerializer
        assert self.view.lookup_field == "pk"
        assert self.view.detail is None

    def test_get_response_without_detail(self):
        """Test get_response when detail is None and no lookup param."""
        response = self.view.get_response(self.view.request)
        assert isinstance(response, Response)
        assert response.data == {"detail": "ok"}
        assert response.status_code == 200

    def test_get_response_with_detail_true(self):
        """Test get_response when detail is True."""
        self.view.detail = True

        # Mock get_object to prevent actual database lookup
        self.view.get_object = MagicMock()

        response = self.view.get_response(self.view.request)
        assert self.view.get_object.called
        assert response.data == {"detail": "ok"}

    def test_get_response_with_lookup_parameter(self):
        """Test get_response when lookup parameter is present."""
        self.view.kwargs = {"pk": "123"}

        # Mock get_object to prevent actual database lookup
        self.view.get_object = MagicMock()

        response = self.view.get_response(self.view.request)
        assert self.view.get_object.called
        assert response.data == {"detail": "ok"}

    def test_get_response_without_lookup_parameter(self):
        """Test get_response when no lookup parameter is present."""
        self.view.kwargs = {}

        # No need to mock get_object as it shouldn't be called
        self.view.get_object = MagicMock()

        response = self.view.get_response(self.view.request)
        assert not self.view.get_object.called
        assert response.data == {"detail": "ok"}

    def test_detail_false_no_get_object_call(self):
        """Test that get_object is not called when detail is False."""
        self.view.detail = False
        self.view.kwargs = {"pk": "123"}

        self.view.get_object = MagicMock()

        response = self.view.get_response(self.view.request)
        assert not self.view.get_object.called
        assert response.data == {"detail": "ok"}

    def test_http_methods(self):
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
def test_http_method_calls_get_response(method_name):
    """Test that each HTTP method calls get_response correctly."""
    view = ChanxAuthView()
    request_factory = RequestFactory()

    # Create a request for the specific method
    request_method = getattr(request_factory, method_name)
    request = request_method("/")
    drf_request = Request(request)

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
