"""
FastAPI fast-channels concrete WebSocket consumer implementation.

This module provides the concrete AsyncJsonWebsocketConsumer class that combines
Chanx's enhanced WebSocket functionality (from the core mixin) with fast-channels'
AsyncJsonWebsocketConsumer base class. This is the main consumer class users should
import when building WebSocket applications with FastAPI and fast-channels.

The concrete consumer inherits from both:
- chanx.core.websocket.AsyncJsonWebsocketConsumer (Chanx mixin with all features)
- fast_channels.consumer.AsyncJsonWebsocketConsumer (fast-channels base)

This multiple inheritance provides:
- Automatic message routing and validation (from Chanx mixin)
- FastAPI fast-channels channel layer integration
- Full compatibility with FastAPI's ASGI application
- Type-safe operation with static type checkers
"""

from typing_extensions import TypeVar

from chanx.core.websocket import ChanxWebsocketConsumerMixin
from chanx.messages.base import BaseMessage
from fast_channels.consumer import (
    AsyncJsonWebsocketConsumer as FastChannelsAsyncJsonWebsocketConsumer,
)
from fast_channels.layers import get_channel_layer

ReceiveEvent = TypeVar("ReceiveEvent", bound=BaseMessage, default=BaseMessage)


class AsyncJsonWebsocketConsumer(  # type: ignore[misc]
    ChanxWebsocketConsumerMixin[ReceiveEvent], FastChannelsAsyncJsonWebsocketConsumer
):
    """
    FastAPI fast-channels WebSocket consumer with Chanx enhanced features.

    Combines Chanx's automatic message handling, type validation, and group
    broadcasting capabilities with fast-channels' WebSocket consumer for FastAPI.

    Features from Chanx mixin:
    - Automatic message type discovery from @ws_handler decorators
    - Type-safe message validation using Pydantic discriminated unions
    - Group broadcasting and channel event system
    - Comprehensive error handling and logging
    - Optional authentication support

    Features from fast-channels:
    - FastAPI ASGI integration
    - fast-channels channel layer support (Redis, in-memory, etc.)
    - WebSocket lifecycle management
    - High-performance async operation

    Usage:
        ```python
        from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
        from chanx.core.decorators import ws_handler

        class MyChatConsumer(AsyncJsonWebsocketConsumer):
            @ws_handler
            async def handle_message(self, message: ChatMessage) -> ChatResponse:
                # Handle incoming messages
                return ChatResponse(...)
        ```

    Note:
        Unlike Django Channels integration, fast-channels does not have built-in
        authentication integration. Users should implement authentication in their
        FastAPI dependency injection or custom authenticator classes.
    """

    channel_layer_alias: str
    get_channel_layer = get_channel_layer  # type: ignore[assignment, unused-ignore]
