"""
Tests for websocket utility functions.

This module tests the various utilities in the websocket.py module
for discovering and transforming WebSocket routes.
"""

from typing import Any
from unittest.mock import MagicMock, Mock, patch

from channels.routing import URLRouter
from django.http import HttpRequest

from chanx.routing import path
from chanx.utils.websocket import (
    RouteInfo,
    _extract_routes_from_router,
    _get_pattern_string_and_params,
    _get_websocket_base_url,
    _traverse_middleware,
    get_websocket_routes,
    transform_routes,
)


class TestWebSocketBaseURL:
    """Tests for the _get_websocket_base_url function."""

    def test_without_request(self) -> None:
        """Test default WebSocket base URL without a request."""
        base_url = _get_websocket_base_url(None)
        assert base_url == "ws://localhost:8000"

    def test_with_insecure_request(self) -> None:
        """Test WebSocket base URL with an insecure request."""
        mock_request = MagicMock(spec=HttpRequest)
        mock_request.get_host.return_value = "example.com"
        mock_request.is_secure.return_value = False

        base_url = _get_websocket_base_url(mock_request)
        assert base_url == "ws://example.com"
        mock_request.get_host.assert_called_once()
        mock_request.is_secure.assert_called_once()

    def test_with_secure_request(self) -> None:
        """Test WebSocket base URL with a secure request."""
        mock_request = MagicMock(spec=HttpRequest)
        mock_request.get_host.return_value = "example.com"
        mock_request.is_secure.return_value = True

        base_url = _get_websocket_base_url(mock_request)
        assert base_url == "wss://example.com"
        mock_request.get_host.assert_called_once()
        mock_request.is_secure.assert_called_once()


class TestGetWebSocketRoutes:
    """Tests for the get_websocket_routes function."""

    @patch("chanx.utils.websocket._get_websocket_base_url")
    @patch("chanx.utils.websocket.get_websocket_application")
    @patch("chanx.utils.websocket._traverse_middleware")
    def test_get_websocket_routes_with_app(
        self, mock_traverse: Mock, mock_get_app: Mock, mock_get_base_url: Mock
    ) -> None:
        """Test route discovery when a WebSocket app is available."""
        # Setup mocks
        mock_request = MagicMock(spec=HttpRequest)
        mock_app = MagicMock()
        mock_base_url = "ws://test.com"

        mock_get_app.return_value = mock_app
        mock_get_base_url.return_value = mock_base_url

        # Call the function
        routes = get_websocket_routes(mock_request)

        # Verify the behavior
        mock_get_base_url.assert_called_once_with(mock_request)
        mock_get_app.assert_called_once()
        mock_traverse.assert_called_once_with(mock_app, "", routes, mock_base_url)

    @patch("chanx.utils.websocket._get_websocket_base_url")
    @patch("chanx.utils.websocket.get_websocket_application")
    @patch("chanx.utils.websocket._traverse_middleware")
    def test_get_websocket_routes_without_app(
        self, mock_traverse: Mock, mock_get_app: Mock, mock_get_base_url: Mock
    ) -> None:
        """Test route discovery when no WebSocket app is available."""
        # Setup mocks
        mock_request = MagicMock(spec=HttpRequest)
        mock_base_url = "ws://test.com"

        mock_get_app.return_value = None
        mock_get_base_url.return_value = mock_base_url

        # Call the function
        routes = get_websocket_routes(mock_request)

        # Verify the behavior
        mock_get_base_url.assert_called_once_with(mock_request)
        mock_get_app.assert_called_once()
        mock_traverse.assert_not_called()
        assert routes == []


class TestTransformRoutes:
    """Tests for the transform_routes function."""

    def test_transform_routes(self) -> None:
        """Test transforming routes with a custom function."""
        # Create sample routes
        routes = [
            RouteInfo(path="test1", handler=MagicMock(), base_url="ws://example.com"),
            RouteInfo(path="test2", handler=MagicMock(), base_url="ws://example.com"),
        ]

        # Define a transformation function
        def transform_to_paths(route: RouteInfo) -> str:
            return route.path

        # Transform the routes
        result = transform_routes(routes, transform_to_paths)

        # Verify the results
        assert result == ["test1", "test2"]

    def test_transform_routes_to_dict(self) -> None:
        """Test transforming routes to dictionary format."""
        # Create sample routes
        mock_handler1 = MagicMock()
        mock_handler1.__class__.__name__ = "TestConsumer1"
        mock_handler2 = MagicMock()
        mock_handler2.__class__.__name__ = "TestConsumer2"

        routes = [
            RouteInfo(path="path1", handler=mock_handler1, base_url="ws://example.com"),
            RouteInfo(path="path2", handler=mock_handler2, base_url="ws://example.com"),
        ]

        # Define a transformation function for dictionary conversion
        def transform_to_dict(route: RouteInfo) -> dict[str, Any]:
            return {
                "path": route.path,
                "handler_type": route.handler.__class__.__name__,
                "url": route.full_url,
            }

        # Transform the routes
        result = transform_routes(routes, transform_to_dict)

        # Verify the results
        expected = [
            {
                "path": "path1",
                "handler_type": "TestConsumer1",
                "url": "ws://example.com/path1",
            },
            {
                "path": "path2",
                "handler_type": "TestConsumer2",
                "url": "ws://example.com/path2",
            },
        ]
        assert result == expected

    def test_empty_routes_list(self) -> None:
        """Test transforming an empty routes list."""
        routes: list[RouteInfo] = []

        def identity(route: RouteInfo) -> RouteInfo:
            return route

        result = transform_routes(routes, identity)
        assert result == []


class TestTraverseMiddleware:
    """Tests for the _traverse_middleware function."""

    def test_traverse_url_router(self) -> None:
        """Test traversing a URLRouter directly."""
        router = MagicMock(spec=URLRouter)
        routes: list[RouteInfo] = []
        base_url = "ws://example.com"

        with patch("chanx.utils.websocket._extract_routes_from_router") as mock_extract:
            _traverse_middleware(router, "", routes, base_url)
            mock_extract.assert_called_once_with(router, "", routes, base_url)

    def test_traverse_none_app(self) -> None:
        """Test traversing with None app."""
        routes: list[RouteInfo] = []
        base_url = "ws://example.com"

        # This should not raise an error
        _traverse_middleware(None, "", routes, base_url)
        assert routes == []

    def test_traverse_middleware_with_inner(self) -> None:
        """Test traversing middleware with inner application."""
        mock_inner = MagicMock()
        mock_app = MagicMock()
        mock_app.inner = mock_inner
        routes: list[RouteInfo] = []
        base_url = "ws://example.com"

        with patch("chanx.utils.websocket._traverse_middleware") as mock_traverse:
            _traverse_middleware(mock_app, "", routes, base_url)
            mock_traverse.assert_called_once_with(mock_inner, "", routes, base_url)

    def test_traverse_middleware_with_app_attr(self) -> None:
        """Test traversing middleware with app attribute."""
        mock_inner = MagicMock()
        mock_app = MagicMock()
        # Remove inner attribute if present
        if hasattr(mock_app, "inner"):
            delattr(mock_app, "inner")
        mock_app.app = mock_inner
        routes: list[RouteInfo] = []
        base_url = "ws://example.com"

        with patch("chanx.utils.websocket._traverse_middleware") as mock_traverse:
            _traverse_middleware(mock_app, "", routes, base_url)
            mock_traverse.assert_called_once_with(mock_inner, "", routes, base_url)

    def test_traverse_middleware_with_application_attr(self) -> None:
        """Test traversing middleware with application attribute."""
        mock_inner = MagicMock()
        mock_app = MagicMock()
        # Remove inner and app attributes if present
        if hasattr(mock_app, "inner"):
            delattr(mock_app, "inner")
        if hasattr(mock_app, "app"):
            delattr(mock_app, "app")
        mock_app.application = mock_inner
        routes: list[RouteInfo] = []
        base_url = "ws://example.com"

        with patch("chanx.utils.websocket._traverse_middleware") as mock_traverse:
            _traverse_middleware(mock_app, "", routes, base_url)
            mock_traverse.assert_called_once_with(mock_inner, "", routes, base_url)

    def test_traverse_middleware_no_inner_app(self) -> None:
        """Test traversing middleware with no inner application found."""
        mock_app = MagicMock()
        # Remove all possible inner app attributes
        if hasattr(mock_app, "inner"):
            delattr(mock_app, "inner")
        if hasattr(mock_app, "app"):
            delattr(mock_app, "app")
        if hasattr(mock_app, "application"):
            delattr(mock_app, "application")

        routes: list[RouteInfo] = []
        base_url = "ws://example.com"

        # This should not call _traverse_middleware again
        with patch("chanx.utils.websocket._traverse_middleware") as mock_traverse:
            _traverse_middleware(mock_app, "", routes, base_url)
            mock_traverse.assert_not_called()


class TestExtractRoutesFromRouter:
    """Tests for the _extract_routes_from_router function."""

    def test_extract_routes_attribute_error(self) -> None:
        """Test handling of AttributeError in _extract_routes_from_router."""
        # Create a router with a route that will cause an AttributeError
        mock_route = MagicMock()
        # Remove necessary attributes to trigger AttributeError
        del mock_route.pattern
        del mock_route.callback

        router = MagicMock(spec=URLRouter)
        router.routes = [mock_route]

        routes: list[RouteInfo] = []
        base_url = "ws://example.com"
        prefix = "test-prefix/"

        with patch("chanx.utils.websocket.logger") as mock_logger:
            _extract_routes_from_router(router, prefix, routes, base_url)
            # Verify the error was logged
            mock_logger.exception.assert_called_once()
            # The routes list should remain empty
            assert routes == []

    def test_extract_routes_general_exception(self) -> None:
        """Test handling of general Exception in _extract_routes_from_router."""
        # Create a router with a route that will cause a general exception
        mock_route = MagicMock()

        # Make the pattern property raise an exception when accessed
        type(mock_route).pattern = property(
            lambda self: (_ for _ in ()).throw(ValueError("Test exception"))
        )

        router = MagicMock(spec=URLRouter)
        router.routes = [mock_route]

        routes: list[RouteInfo] = []
        base_url = "ws://example.com"
        prefix = "test-prefix/"

        with patch("chanx.utils.websocket.logger") as mock_logger:
            _extract_routes_from_router(router, prefix, routes, base_url)
            # Verify the error was logged
            mock_logger.exception.assert_called_once()
            # The routes list should remain empty
            assert routes == []


class TestGetPatternStringAndParams:
    """Tests for the _get_pattern_string_and_params function."""

    def test_get_pattern_with_pattern_attribute_and_nested_pattern(self) -> None:
        """Test extracting pattern string from route with nested pattern."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^test-pattern$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "test-pattern"
        assert params is None

    def test_get_pattern_with_pattern_attribute_no_nested(self) -> None:
        """Test extracting pattern string from route with non-nested pattern."""
        mock_route = MagicMock()
        mock_route.pattern = "^another-pattern$"

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "another-pattern"
        assert params is None

    def test_get_pattern_with_regex_path_parameters(self) -> None:
        """Test extracting pattern string with regex path parameters."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^user/(?P<user_id>[0-9]+)/profile$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "user/(?P<user_id>[0-9]+)/profile"
        assert params == {"user_id": "[0-9]+"}

    def test_get_pattern_with_multiple_regex_path_parameters(self) -> None:
        """Test extracting pattern string with multiple regex path parameters."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = (
            "^projects/(?P<project_id>[0-9]+)/tasks/(?P<task_id>[a-z0-9]+)$"
        )
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "projects/(?P<project_id>[0-9]+)/tasks/(?P<task_id>[a-z0-9]+)"
        assert params == {"project_id": "[0-9]+", "task_id": "[a-z0-9]+"}

    def test_get_pattern_with_django_str_parameter(self) -> None:
        """Test extracting Django-style string path parameter."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^chat/<str:room_name>/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "chat/<str:room_name>/"
        assert params == {"room_name": "[^/]+"}

    def test_get_pattern_with_django_int_parameter(self) -> None:
        """Test extracting Django-style integer path parameter."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^user/<int:user_id>/profile/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "user/<int:user_id>/profile/"
        assert params == {"user_id": "[0-9]+"}

    def test_get_pattern_with_django_slug_parameter(self) -> None:
        """Test extracting Django-style slug path parameter."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^article/<slug:article_slug>/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "article/<slug:article_slug>/"
        assert params == {"article_slug": "[-a-zA-Z0-9_]+"}

    def test_get_pattern_with_django_uuid_parameter(self) -> None:
        """Test extracting Django-style UUID path parameter."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^object/<uuid:object_id>/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "object/<uuid:object_id>/"
        assert params == {
            "object_id": "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        }

    def test_get_pattern_with_django_path_parameter(self) -> None:
        """Test extracting Django-style path parameter."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^file/<path:file_path>/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "file/<path:file_path>/"
        assert params == {"file_path": ".+"}

    def test_get_pattern_with_unknown_django_converter(self) -> None:
        """Test extracting Django-style parameter with unknown converter type."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^item/<custom:item_id>/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "item/<custom:item_id>/"
        # Unknown converter types default to [^/]+
        assert params == {"item_id": "[^/]+"}

    def test_get_pattern_with_multiple_django_parameters(self) -> None:
        """Test extracting multiple Django-style path parameters."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^<str:category>/<int:year>/<slug:title>/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "<str:category>/<int:year>/<slug:title>/"
        assert params == {
            "category": "[^/]+",
            "year": "[0-9]+",
            "title": "[-a-zA-Z0-9_]+",
        }

    def test_get_pattern_with_mixed_parameters(self) -> None:
        """Test extracting both Django-style and regex path parameters."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^<str:room_name>/(?P<message_id>[0-9]+)/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "<str:room_name>/(?P<message_id>[0-9]+)/"
        assert params == {
            "room_name": "[^/]+",
            "message_id": "[0-9]+",
        }

    def test_get_pattern_no_parameters(self) -> None:
        """Test extracting pattern with no parameters."""
        mock_route = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.pattern = "^simple/path/$"
        mock_route.pattern = mock_pattern

        pattern, params = _get_pattern_string_and_params(mock_route)
        assert pattern == "simple/path/"
        assert params is None


class TestIntegration:
    """Integration tests for the WebSocket utils."""

    @patch("chanx.utils.websocket.get_websocket_application")
    def test_route_discovery_integration(self, mock_get_app: Mock) -> None:
        """Test the route discovery process with a realistic URLRouter setup."""
        # Create mock consumer and handler
        mock_consumer = MagicMock()
        mock_consumer.__class__.__name__ = "TestConsumer"
        mock_handler = MagicMock()

        # Set up a simple URL routing structure
        nested_router = URLRouter(
            [
                path("nested/", mock_consumer),
            ]
        )

        main_router = URLRouter(
            [
                path("api/", mock_handler),
                path("ws/", nested_router),
            ]
        )

        # Set up our mock to return this router
        mock_get_app.return_value = main_router

        # Call the function being tested
        mock_request = MagicMock(spec=HttpRequest)
        mock_request.get_host.return_value = "example.com"
        mock_request.is_secure.return_value = False

        routes = get_websocket_routes(mock_request)

        # Verify the correct routes were discovered
        assert len(routes) == 2

        # Check the first route
        assert routes[0].path == "api/"
        assert routes[0].handler == mock_handler
        assert routes[0].base_url == "ws://example.com"
        assert routes[0].full_url == "ws://example.com/api/"

        # Check the second (nested) route
        assert routes[1].path == "ws/nested/"
        assert routes[1].handler == mock_consumer
        assert routes[1].base_url == "ws://example.com"
        assert routes[1].full_url == "ws://example.com/ws/nested/"

    @patch("chanx.utils.websocket.get_websocket_application")
    def test_route_discovery_with_django_path_params(self, mock_get_app: Mock) -> None:
        """Test route discovery with Django-style path parameters."""
        # Create mock consumers
        mock_chat_consumer = MagicMock()
        mock_chat_consumer.__class__.__name__ = "ChatConsumer"
        mock_user_consumer = MagicMock()
        mock_user_consumer.__class__.__name__ = "UserConsumer"

        # Create a route that will be converted to Django-style path
        # We need to mock this because we can't easily create real Django URLRoute objects
        mock_route1 = MagicMock()
        mock_pattern1 = MagicMock()
        mock_pattern1.pattern = "^chat/<str:room_name>/$"
        mock_route1.pattern = mock_pattern1
        mock_route1.callback = mock_chat_consumer

        mock_route2 = MagicMock()
        mock_pattern2 = MagicMock()
        mock_pattern2.pattern = "^user/<int:user_id>/profile/$"
        mock_route2.pattern = mock_pattern2
        mock_route2.callback = mock_user_consumer

        # Create a router with these routes
        main_router = MagicMock(spec=URLRouter)
        main_router.routes = [mock_route1, mock_route2]

        # Set up our mock to return this router
        mock_get_app.return_value = main_router

        # Call the function being tested
        mock_request = MagicMock(spec=HttpRequest)
        mock_request.get_host.return_value = "example.com"
        mock_request.is_secure.return_value = False

        routes = get_websocket_routes(mock_request)

        # Verify the correct routes were discovered
        assert len(routes) == 2

        # Check the first route (with str parameter)
        assert routes[0].path == "chat/<str:room_name>/"
        assert routes[0].handler == mock_chat_consumer
        assert routes[0].base_url == "ws://example.com"
        assert routes[0].path_params == {"room_name": "[^/]+"}
        assert routes[0].friendly_path == "chat/:room_name/"

        # Check the second route (with int parameter)
        assert routes[1].path == "user/<int:user_id>/profile/"
        assert routes[1].handler == mock_user_consumer
        assert routes[1].base_url == "ws://example.com"
        assert routes[1].path_params == {"user_id": "[0-9]+"}
        assert routes[1].friendly_path == "user/:user_id/profile/"
