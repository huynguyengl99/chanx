"""
Utility functions for WebSocket route discovery and inspection.

This module provides tools to dynamically discover WebSocket routes
in a Django Channels application and generate example messages for
WebSocket consumer endpoints.
"""

import inspect
from types import UnionType
from typing import (
    Any,
    TypedDict,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from channels.routing import URLRouter, get_default_application
from django.http import HttpRequest

from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel

from chanx.messages.base import BaseIncomingMessage
from chanx.utils.logging import logger


class MessageExample(TypedDict):
    """Type definition for WebSocket message examples."""

    name: str
    description: str
    example: dict[str, Any]


class WebSocketRoute(TypedDict, total=False):
    """Type definition for WebSocket route information.

    Attributes:
        name: The name of the WebSocket consumer.
        url: The full URL to connect to this WebSocket endpoint.
        description: A description of the endpoint extracted from docstrings.
        message_examples: A list of example messages that can be sent to this endpoint.
    """

    name: str
    url: str
    description: str
    message_examples: list[MessageExample]


def get_websocket_routes(request: HttpRequest | None = None) -> list[WebSocketRoute]:
    """
    Extract all WebSocket routes from the ASGI application.

    This function traverses the Django Channels routing configuration
    to discover all available WebSocket endpoints, their paths, and
    generates example messages for each endpoint based on the
    message schema defined in the consumer.

    Args:
        request: The HTTP request object, used to determine the current domain.
               If None, defaults to localhost:8000.

    Returns:
        A list of dictionaries containing route information including URL,
        description, and example messages.
    """
    endpoints: list[WebSocketRoute] = []

    # Determine the WebSocket base URL based on the request
    ws_base_url: str = _get_websocket_base_url(request)

    # Extract the WebSocket protocol handler from the ASGI application
    application = get_default_application()
    if hasattr(application, "application_mapping"):
        # If it's a ProtocolTypeRouter
        ws_app: Any = application.application_mapping.get("websocket")

        # Extract routes
        if ws_app:
            _traverse_middleware(ws_app, "", endpoints, ws_base_url)

    return endpoints


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
        return "ws://localhost:8000"

    # Get the current domain from the request
    domain: str = request.get_host()

    # Determine if we should use secure WebSockets (wss://) based on the request
    is_secure: bool = request.is_secure()
    protocol: str = "wss://" if is_secure else "ws://"

    return f"{protocol}{domain}"


def _traverse_middleware(
    app: Any, prefix: str, endpoints: list[WebSocketRoute], ws_base_url: str
) -> None:
    """
    Traverse through middleware layers to find the URLRouter.

    Recursively explores the middleware stack to find URLRouter instances
    and extract route information from them. It uses the fact that
    middleware typically stores the inner app as self.inner.

    Args:
        app: The current application or middleware to traverse.
        prefix: URL prefix accumulated so far.
        endpoints: List to store discovered endpoints.
        ws_base_url: Base URL for WebSocket connections.
    """
    # Skip if app is None
    if app is None:
        return

    # If it's a URLRouter, extract routes
    if isinstance(app, URLRouter):
        _extract_routes_from_router(app, prefix, endpoints, ws_base_url)
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
        _traverse_middleware(inner_app, prefix, endpoints, ws_base_url)


def _extract_routes_from_router(
    router: URLRouter, prefix: str, endpoints: list[WebSocketRoute], ws_base_url: str
) -> None:
    """
    Extract routes from a URLRouter object.

    Processes each route in the router, extracting path patterns and
    handler information, and recursively traversing nested routers.

    Args:
        router: The router to extract routes from.
        prefix: URL prefix accumulated so far.
        endpoints: List to store discovered endpoints.
        ws_base_url: Base URL for WebSocket connections.
    """
    for route in router.routes:
        try:
            # Get the pattern string
            pattern: str = _get_pattern_string(route)

            # Build the full path
            full_path: str = f"{prefix}{pattern}"

            # Get the handler
            handler: Any = route.callback

            # If it's another router, recurse into it
            if isinstance(handler, URLRouter):
                _extract_routes_from_router(handler, full_path, endpoints, ws_base_url)
            else:
                # For consumers, get info with message examples
                endpoint_info: WebSocketRoute = _get_handler_info(
                    handler, full_path, ws_base_url
                )
                endpoints.append(endpoint_info)
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


def _get_pattern_string(route: Any) -> str:
    """
    Extract pattern string from a route object.

    Handles different route pattern implementations to extract
    the URL pattern string.

    Args:
        route: The route object to extract pattern from.

    Returns:
        The cleaned URL pattern string.
    """
    if hasattr(route, "pattern"):
        # For URLRoute
        if hasattr(route.pattern, "pattern"):
            pattern: str = route.pattern.pattern
        else:
            # For RoutePattern
            pattern = str(route.pattern)
    else:
        pattern = str(route)

    # Clean up the pattern string
    pattern = pattern.replace("^", "").replace("$", "")
    return pattern


def _get_handler_info(handler: Any, path: str, ws_base_url: str) -> WebSocketRoute:
    """
    Extract information about a route handler.

    Extracts metadata from a WebSocket consumer including its name,
    description, and message schema, and generates example messages.

    Args:
        handler: The route handler (consumer).
        path: The full URL path.
        ws_base_url: Base URL for WebSocket connections.

    Returns:
        Information about the handler including name, URL, description,
        and example messages.
    """
    # Default values
    name: str = getattr(handler, "__name__", "Unknown")
    description: str = handler.__doc__ or ""
    message_examples: list[MessageExample] = []

    try:
        # Extract the consumer class if it's an as_asgi wrapper
        consumer_class: Any = handler.consumer_class

        # Try to get message schema from the consumer class
        incoming_message_schema: type[BaseIncomingMessage] | None = getattr(
            consumer_class, "INCOMING_MESSAGE_SCHEMA", None
        )

        if incoming_message_schema:
            message_examples = get_message_examples(incoming_message_schema)
    except AttributeError as e:
        # Log the error but continue with empty message examples
        logger.debug(f"Could not extract message schema for {name}: {str(e)}")

    return {
        "name": name,
        "url": f"{ws_base_url}/{path}",
        "description": description.strip(),
        "message_examples": message_examples,
    }


def _create_example(msg_type: type[BaseModel]) -> MessageExample:
    """
    Create an example for a specific message type.

    Helper function to generate a standardized example for a message type.

    Args:
        msg_type: The message type to create an example for.

    Returns:
        A formatted example with name, description, and sample data.
    """
    description = inspect.getdoc(msg_type) or f"Example of {msg_type.__name__}"

    # Create the example using the factory
    factory = ModelFactory.create_factory(model=msg_type)
    example: BaseModel = factory.build()

    return {
        "name": msg_type.__name__,
        "description": description,
        "example": example.model_dump(),
    }


def get_message_examples(
    message_type: type[BaseIncomingMessage] | None,
) -> list[MessageExample]:
    """
    Generate examples for message types using discriminator pattern.

    Creates example messages for each possible message type in a discriminated
    union. This is useful for providing example WebSocket messages in
    documentation or testing tools.

    Args:
        message_type: The root message type (typically a Union type with discriminator)

    Returns:
        A list of example messages that can be used in the playground or docs
    """
    examples: list[MessageExample] = []

    # Find the discriminated union field in the Message class
    try:
        type_hints = get_type_hints(message_type)

        message_type = type_hints["message"]
    except (TypeError, AttributeError, KeyError):
        # Handle various type inspection errors
        logger.exception(f"Could not get type hints for {message_type}")
        return examples

    if not message_type:
        return examples

    # If it's not a union type, just generate a single example
    origin = get_origin(message_type)
    if not (origin is Union or origin is UnionType):
        return [_create_example(message_type)]

    # For each message type in the union, create an example
    union_types = get_args(message_type)
    for msg_type in union_types:
        examples.append(_create_example(msg_type))

    return examples
