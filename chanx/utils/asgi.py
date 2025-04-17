"""
ASGI application utility functions.

This module provides utilities for working with ASGI applications,
particularly for extracting the WebSocket application from the ASGI
configuration with all its middleware layers.
"""

from typing import Any

from channels.routing import get_default_application


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
