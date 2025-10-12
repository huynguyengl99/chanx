"""
Django Channels concrete WebSocket consumer implementation.

This module provides the concrete AsyncJsonWebsocketConsumer class that combines
Chanx's enhanced WebSocket functionality (from the core mixin) with Django Channels'
AsyncJsonWebsocketConsumer base class. This is the main consumer class users should
import when building WebSocket applications with Django and Channels.

The concrete consumer inherits from both:
- chanx.core.websocket.AsyncJsonWebsocketConsumer (Chanx mixin with all features)
- channels.generic.websocket.AsyncJsonWebsocketConsumer (Django Channels base)

This multiple inheritance provides:
- Automatic message routing and validation (from Chanx mixin)
- Django Channels channel layer integration
- Full compatibility with Django's ASGI application
- Type-safe operation with static type checkers
"""

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as ChannelsAsyncJsonWebsocketConsumer,
)
from channels.layers import get_channel_layer

from typing_extensions import TypeVar

from chanx.core.websocket import ChanxWebsocketConsumerMixin
from chanx.messages.base import BaseMessage

ReceiveEvent = TypeVar("ReceiveEvent", bound=BaseMessage, default=BaseMessage)


class AsyncJsonWebsocketConsumer(  # type: ignore[misc]
    ChanxWebsocketConsumerMixin[ReceiveEvent], ChannelsAsyncJsonWebsocketConsumer
):
    """
    Django Channels WebSocket consumer with Chanx enhanced features.

    Combines Chanx's automatic message handling, type validation, authentication,
    and group broadcasting capabilities with Django Channels' WebSocket consumer.

    Features from Chanx mixin:
    - Automatic message type discovery from @ws_handler decorators
    - Type-safe message validation using Pydantic discriminated unions
    - Built-in authentication with Django REST Framework integration
    - Group broadcasting and channel event system
    - Comprehensive error handling and logging

    Features from Django Channels:
    - Django ASGI integration
    - Django channel layer support (Redis, in-memory, etc.)
    - Django authentication and session support
    - WebSocket lifecycle management

    Usage:
        ```python
        from chanx.channels.websocket import AsyncJsonWebsocketConsumer
        from chanx.channels.authenticator import DjangoAuthenticator
        from chanx.core.decorators import ws_handler

        class MyChatConsumer(AsyncJsonWebsocketConsumer):
            authenticator_class = DjangoAuthenticator

            @ws_handler
            async def handle_message(self, message: ChatMessage) -> ChatResponse:
                # Handle incoming messages
                return ChatResponse(...)
        ```
    """

    get_channel_layer = get_channel_layer  # type: ignore[assignment, unused-ignore]
