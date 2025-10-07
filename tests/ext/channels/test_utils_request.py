from django.test import TestCase

from chanx.ext.channels.utils import request_from_scope


class TestRequestUtils(TestCase):
    """Test cases for HTTP request utility functions."""

    def test_request_from_scope_with_headers(self) -> None:
        """Test request_from_scope handles headers properly."""
        # Create a scope with headers
        scope = {
            "path": "/test-path/",
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-test-header", b"test-value"),
                (b"host", b"example.com"),
            ],
        }

        # Get request from scope
        request = request_from_scope(scope, "get")

        # Verify headers were processed correctly
        assert request.META["HTTP_CONTENT_TYPE"] == "application/json"
        assert request.META["HTTP_X_TEST_HEADER"] == "test-value"
        assert request.META["HTTP_HOST"] == "example.com"

    def test_request_from_scope_header_with_http_prefix(self) -> None:
        """Test headers already starting with HTTP_ don't get double-prefixed."""
        scope = {
            "headers": [
                (b"http_already_prefixed", b"test-value"),
            ]
        }

        request = request_from_scope(scope, "get")

        # Verify the header wasn't double-prefixed
        assert "HTTP_HTTP_ALREADY_PREFIXED" not in request.META
        assert request.META["HTTP_ALREADY_PREFIXED"] == "test-value"

    def test_request_from_scope_header_without_http_prefix(self) -> None:
        """Test headers without HTTP_ prefix get properly prefixed."""
        scope = {
            "headers": [
                (b"normal-header", b"test-value"),
            ]
        }

        request = request_from_scope(scope, "get")

        # Verify the HTTP_ prefix was added
        assert request.META["HTTP_NORMAL_HEADER"] == "test-value"
