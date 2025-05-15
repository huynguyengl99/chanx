"""
WebSocket route discovery utilities.

This module provides tools to discover and traverse WebSocket routes
in a Django Channels application. It focuses on the generic mechanism
of route discovery that can be used by various components.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast

from channels.routing import URLRouter
from django.http import HttpRequest

from chanx.settings import chanx_settings
from chanx.utils.asgi import get_websocket_application
from chanx.utils.logging import logger

if TYPE_CHECKING:
    from channels.routing import (
        _ExtendedURLPattern,  # pragma: no cover ; TYPE CHECK only
    )
else:
    _ExtendedURLPattern = Any

# Regular expressions for extracting path parameters
REGEX_PARAM_PATTERN = r"\(\?P<([^>]+)>([^)]+)\)"
DJANGO_PARAM_PATTERN = r"<(\w+):(\w+)>"

# Django path converter mappings to regex patterns
DJANGO_PATH_CONVERTERS = {
    "str": r"[^/]+",
    "int": r"[0-9]+",
    "slug": r"[-a-zA-Z0-9_]+",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "path": r".+",
}

# Type for route callbacks/handlers
RouteHandler = TypeVar("RouteHandler")


# Dataclass for route information
@dataclass(frozen=True)
class RouteInfo:
    """WebSocket route information.

    Attributes:
        path: The URL path pattern for the WebSocket route.
        handler: The consumer or handler function for this route.
        base_url: The base WebSocket URL (e.g., ws://domain.com).
        path_params: Dictionary of path parameters with their regex patterns.
    """

    path: str
    handler: Any  # Using Any instead of RouteHandler for broader compatibility
    base_url: str
    path_params: dict[str, str] | None = None

    @property
    def full_url(self) -> str:
        """Get the full WebSocket URL for this route."""
        return f"{self.base_url}/{self.path}"

    @property
    def friendly_path(self) -> str:
        """Get a user-friendly path with :param format instead of regex."""
        if not self.path_params:
            return self.path

        path = self.path
        for param_name, pattern in self.path_params.items():
            # Replace regex patterns with :param format
            path = path.replace(f"(?P<{param_name}>{pattern})", f":{param_name}")
            # Also handle Django-style path parameters
            path = re.sub(rf"<\w+:{param_name}>", f":{param_name}", path)
        return path


# Type variable for the transformation result
T = TypeVar("T")


def get_websocket_routes(request: HttpRequest | None = None) -> list[RouteInfo]:
    """
    Discover all WebSocket routes from the ASGI application.

    This function traverses the Django Channels routing configuration
    to discover all available WebSocket endpoints and their handlers.
    The discovered routes can be used for various purposes like documentation,
    testing, or validation.

    Args:
        request: The HTTP request object, used to determine the current domain.
               If None, defaults to localhost:8000.

    Returns:
        A list of RouteInfo objects containing path, handler, and base_url for each WebSocket route.
    """
    routes: list[RouteInfo] = []

    # Determine the WebSocket base URL based on the request
    ws_base_url: str = _get_websocket_base_url(request)

    # Extract the WebSocket protocol handler from the ASGI application
    ws_app = get_websocket_application()

    # Extract routes if WebSocket app is found
    if ws_app:
        _traverse_middleware(ws_app, "", routes, ws_base_url)

    return routes


def _get_websocket_base_url(request: HttpRequest | None) -> str:
    """
    Determine the WebSocket base URL based on the request.

    Constructs a WebSocket URL (ws:// or wss://) based on the
    domain in the request object.

    Args:
        request: The HTTP request object.

    Returns:
        The WebSocket base URL (ws:// or wss:// followed by domain).
    """
    if request is None:
        return chanx_settings.WEBSOCKET_BASE_URL

    # Get the current domain from the request
    domain: str = request.get_host()

    # Determine if we should use secure WebSockets (wss://) based on the request
    is_secure: bool = request.is_secure()
    protocol: str = "wss://" if is_secure else "ws://"

    return f"{protocol}{domain}"


def _traverse_middleware(
    app: Any, prefix: str, routes: list[RouteInfo], ws_base_url: str
) -> None:
    """
    Traverse through middleware layers to find the URLRouter.

    Recursively explores the middleware stack to find URLRouter instances
    and extract route information from them.

    Args:
        app: The current application or middleware to traverse.
        prefix: URL prefix accumulated so far.
        routes: List to store discovered routes.
        ws_base_url: Base URL for WebSocket connections.
    """
    # Skip if app is None
    if app is None:
        return

    # If it's a URLRouter, extract routes
    if isinstance(app, URLRouter):
        _extract_routes_from_router(app, prefix, routes, ws_base_url)
        return

    # Try to access the inner application (standard middleware pattern)
    inner_app: Any | None = getattr(app, "inner", None)

    # If inner isn't found, try other common attributes that might hold the next app
    if inner_app is None:
        for attr_name in ["app", "application"]:
            inner_app = getattr(app, attr_name, None)
            if inner_app is not None:
                break

    # If we found an inner app, continue traversal
    if inner_app is not None:
        _traverse_middleware(inner_app, prefix, routes, ws_base_url)


def _extract_routes_from_router(
    router: URLRouter, prefix: str, routes: list[RouteInfo], ws_base_url: str
) -> None:
    """
    Extract routes from a URLRouter object.

    Processes each route in the router, extracting path patterns and
    handler information, and recursively traversing nested routers.

    Args:
        router: The router to extract routes from.
        prefix: URL prefix accumulated so far.
        routes: List to store discovered RouteInfo objects.
        ws_base_url: Base URL for WebSocket connections.
    """
    router_routes = cast(list[_ExtendedURLPattern], router.routes)
    for route in router_routes:
        try:
            # Get the pattern string and extract path parameters
            pattern, path_params = _get_pattern_string_and_params(route)

            # Build the full path
            full_path: str = f"{prefix}{pattern}"

            # Get the handler
            handler = route.callback

            # If it's another router, recurse into it
            if isinstance(handler, URLRouter):
                _extract_routes_from_router(handler, full_path, routes, ws_base_url)
            else:
                # For consumers, add to the routes list as a RouteInfo dataclass instance
                routes.append(
                    RouteInfo(
                        path=full_path,
                        handler=handler,
                        base_url=ws_base_url,
                        path_params=path_params,
                    )
                )
        except AttributeError as e:
            # More specific error for attribute issues
            logger.exception(
                f"AttributeError while parsing route: {ws_base_url}/{prefix}. Error: {str(e)}"
            )
        except Exception as e:
            # For other unexpected errors
            logger.exception(
                f"Error parsing route: {ws_base_url}/{prefix}. Error: {str(e)}"
            )


def _get_pattern_string_and_params(route: Any) -> tuple[str, dict[str, str] | None]:
    """
    Extract pattern string and path parameters from a route object.

    Handles different route pattern implementations to extract
    the URL pattern string and identified named path parameters.

    Supports both Django-style path parameters (<type:name>) and regex patterns.

    Args:
        route: The route object to extract pattern from.

    Returns:
        A tuple containing:
        - The cleaned URL pattern string
        - Dictionary of path parameters with their regex patterns, or None if no parameters
    """
    # Get the pattern string
    if hasattr(route, "pattern"):
        # For URLRoute
        if hasattr(route.pattern, "pattern"):
            pattern: str = route.pattern.pattern
        else:
            # For RoutePattern
            pattern = str(route.pattern)
    else:
        pattern = str(route)

    # Dictionary to store path parameters
    path_params: dict[str, str] = {}

    # First, extract regex-style parameters: (?P<name>pattern)
    regex_matches = re.findall(REGEX_PARAM_PATTERN, pattern)

    if regex_matches:
        for name, regex_pattern in regex_matches:
            path_params[name] = regex_pattern

    # Second, extract Django-style path parameters: <type:name>
    django_matches = re.findall(DJANGO_PARAM_PATTERN, pattern)

    if django_matches:
        for converter_type, param_name in django_matches:
            # Get the regex pattern for this converter type
            regex_pattern = DJANGO_PATH_CONVERTERS.get(converter_type, r"[^/]+")
            path_params[param_name] = regex_pattern

    # Clean up the pattern string (remove ^ and $ anchors)
    pattern = pattern.replace("^", "").replace("$", "")

    return pattern, path_params if path_params else None


# Additional helper for applying a transformation function to all routes
def transform_routes(
    routes: list[RouteInfo], transform_fn: Callable[[RouteInfo], T]
) -> list[T]:
    """
    Apply a transformation function to all discovered routes.

    This helper function applies a custom transformation to each route,
    allowing for flexible processing of route information.

    Args:
        routes: List of RouteInfo dataclass instances
        transform_fn: Function to transform each route into the desired format

    Returns:
        List of transformed route information with the type determined by transform_fn
    """
    return [transform_fn(route) for route in routes]
