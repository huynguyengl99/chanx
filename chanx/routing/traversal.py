"""
Generic middleware traversal utilities for route discovery.

This module provides the common logic for traversing middleware stacks
to discover routes, regardless of the specific framework implementation.
"""

from typing import Any, Protocol

from chanx.routing.discovery import RouteInfo
from chanx.utils.logging import logger


class RouteExtractor(Protocol):
    """Protocol for route extraction functions.

    This protocol defines the interface that extract_routes_fn implementations
    must follow. It matches the signature of RouteDiscovery.extract_routes_from_router.
    """

    def __call__(
        self,
        router: Any,
        prefix: str,
        routes: list[RouteInfo],
        base_url: str,
    ) -> None:
        """
        Extract routes from a router-like application object.

        Args:
            router: The router object to extract routes from (e.g., URLRouter)
            prefix: URL prefix accumulated so far
            routes: List to append discovered RouteInfo objects to
            base_url: Base URL for WebSocket connections

        Raises:
            TypeError: If the router object is not of the expected type
        """
        ...


class MiddlewareTraverser(Protocol):
    """Protocol for middleware traversal implementations."""

    def traverse(self, app: Any, prefix: str = "") -> list[Any]:
        """
        Traverse middleware stack and discover routes.

        Args:
            app: The ASGI application or middleware to traverse
            prefix: URL prefix accumulated so far

        Returns:
            List of discovered routes
        """
        ...


def traverse_middleware_stack(
    app: Any,
    prefix: str,
    routes: list[RouteInfo],
    base_url: str,
    extract_routes_fn: RouteExtractor,
) -> None:
    """
    Generic middleware traversal function.

    Recursively explores the middleware stack to find router instances
    and extract route information from them using the provided extraction function.

    This is framework-agnostic and can be used by different routing implementations.

    Args:
        app: The current application or middleware to traverse.
        prefix: URL prefix accumulated so far.
        routes: List to store discovered RouteInfo objects.
        base_url: Base URL for WebSocket connections.
        extract_routes_fn: Function to extract routes from router objects.
    """
    # Skip if app is None
    if app is None:
        return

    # Try the extraction function first (for router-like objects)
    try:
        extract_routes_fn(app, prefix, routes, base_url)
        return
    except (AttributeError, TypeError):
        # Not a router object, continue traversing middleware
        pass

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
        traverse_middleware_stack(
            inner_app, prefix, routes, base_url, extract_routes_fn
        )
    else:
        logger.debug(f"End of middleware traversal at {type(app).__name__}")
