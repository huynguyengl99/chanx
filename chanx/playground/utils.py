"""
WebSocket playground utilities.

This module provides specialized utilities for the WebSocket playground,
transforming route information into a format suitable for display and interaction.
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

from django.http import HttpRequest

from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel

from chanx.messages.base import BaseIncomingMessage
from chanx.utils.websocket import RouteInfo, get_websocket_routes, transform_routes


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


def get_playground_websocket_routes(
    request: HttpRequest | None = None,
) -> list[WebSocketRoute]:
    """
    Get WebSocket routes formatted for the playground.

    Uses the core WebSocket route discovery mechanism and transforms the routes
    into a format suitable for the playground UI, including example messages.

    Args:
        request: The HTTP request object, used to determine the current domain.
               If None, defaults to localhost:8000.

    Returns:
        A list of WebSocketRoute objects with UI-friendly information.
    """
    # Get raw routes from the core utility
    raw_routes = get_websocket_routes(request)

    # Transform routes into the format needed for the playground
    return transform_routes(raw_routes, _transform_route_for_playground)


def _transform_route_for_playground(route: RouteInfo) -> WebSocketRoute:
    """
    Transform a raw route into a playground-friendly format.

    This function extracts metadata from a WebSocket consumer and formats it
    for display in the playground UI, including generating example messages.

    Args:
        route: The RouteInfo dataclass instance

    Returns:
        A WebSocketRoute with UI-friendly information
    """
    # Get handler info with examples for the playground
    return _get_handler_info(
        handler=route.handler, path=route.path, ws_base_url=route.base_url
    )


def _get_handler_info(handler: Any, path: str, ws_base_url: str) -> WebSocketRoute:
    """
    Extract information about a route handler for the playground.

    Extracts metadata from a WebSocket consumer including its name,
    description, and message schema, and generates example messages.

    Args:
        handler: The route handler (consumer).
        path: The full URL path.
        ws_base_url: Base URL for WebSocket connections.

    Returns:
        Information about the handler formatted for the playground.
    """
    # Default values
    name: str = getattr(handler, "__name__", "Unknown")
    description: str = handler.__doc__ or ""

    # Extract the consumer class if it's an as_asgi wrapper
    consumer_class: Any = handler.consumer_class

    # Try to get message schema from the consumer class
    incoming_message_schema: type[BaseIncomingMessage] = (
        consumer_class.INCOMING_MESSAGE_SCHEMA
    )

    message_examples = get_message_examples(incoming_message_schema)

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
    description: str = inspect.getdoc(msg_type) or f"Example of {msg_type.__name__}"

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
    type_hints = get_type_hints(message_type)

    message_field_type = type_hints["message"]

    # If it's not a union type, just generate a single example
    origin = get_origin(message_field_type)
    if not (origin is Union or origin is UnionType):
        return [_create_example(message_field_type)]

    # For each message type in the union, create an example
    union_types = get_args(message_field_type)
    for msg_type in union_types:
        examples.append(_create_example(msg_type))

    return examples
