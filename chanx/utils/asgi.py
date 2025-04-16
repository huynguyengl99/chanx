"""
ASGI application utility functions.

This module provides utilities for working with ASGI applications,
particularly for extracting the WebSocket application from the ASGI
configuration with all its middleware layers.
"""

from typing import Any

from channels.routing import URLRouter, get_default_application


def get_websocket_application() -> Any | None:
    """
    Extract the WebSocket application from the ASGI configuration.

    This function retrieves the WebSocket handler from the ASGI application,
    including all middleware layers like authentication, origin validation, etc.

    Returns:
        The WebSocket application with all middleware, or None if not found.
    """
    application = get_default_application()

    # Check if it's a ProtocolTypeRouter
    if hasattr(application, "application_mapping"):
        # Extract the WebSocket protocol handler with all its middleware
        ws_app = application.application_mapping.get("websocket")
        return ws_app

    return None


def get_websocket_router() -> URLRouter | None:
    """
    Find the URLRouter within the WebSocket application stack.

    This function traverses the middleware stack to find the URLRouter
    that contains the actual route definitions.

    Returns:
        The URLRouter instance if found, or None otherwise.
    """
    ws_app = get_websocket_application()
    if not ws_app:
        return None

    # Traverse the middleware stack to find the URLRouter
    app = ws_app
    while app is not None:
        if isinstance(app, URLRouter):
            return app

        # Try to access the inner application (standard middleware pattern)
        inner_app = getattr(app, "inner", None)

        # If inner isn't found, try other common attributes
        if inner_app is None:
            for attr_name in ["app", "application"]:
                inner_app = getattr(app, attr_name, None)
                if inner_app is not None:
                    break

        app = inner_app

    return None
