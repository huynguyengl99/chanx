"""
FastAPI fast-channels concrete WebSocket demultiplexer implementation.

This module provides the concrete AsyncJsonWebsocketDemultiplexer class that
combines Chanx's multiplexing functionality (from the core mixin) with
fast-channels' AsyncJsonWebsocketConsumer base class. This is the class users
should import to serve several consumers over a single route with FastAPI.

The concrete demultiplexer inherits from both:
- chanx.core.multiplex.ChanxDemultiplexerMixin (Chanx mixin with all features)
- fast_channels.consumer.AsyncJsonWebsocketConsumer (fast-channels base)
"""

from typing_extensions import TypeVar

from chanx.core.multiplex import ChanxDemultiplexerMixin
from chanx.messages.base import BaseMessage
from fast_channels.consumer import (
    AsyncJsonWebsocketConsumer as FastChannelsAsyncJsonWebsocketConsumer,
)
from fast_channels.layers import get_channel_layer

ReceiveEvent = TypeVar("ReceiveEvent", bound=BaseMessage, default=BaseMessage)


class AsyncJsonWebsocketDemultiplexer(
    ChanxDemultiplexerMixin[ReceiveEvent], FastChannelsAsyncJsonWebsocketConsumer
):
    """
    FastAPI fast-channels WebSocket demultiplexer with Chanx enhanced features.

    Serves several Chanx consumers over one connection, routing frames by the
    envelope field. Declare the sub-consumers with an explicit mapping::

        class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
            consumers = {
                "chat": ChatConsumer,
                "notifications": NotificationConsumer,
            }

    Features from Chanx mixin:

    - Envelope-based routing to any number of sub-consumers
    - Sub-consumers keep their own channel name, groups and channel events
    - Fall-through to the demultiplexer's own @ws_handler methods
    - Isolation of a sub-consumer that closes, without losing the shared socket
    - Optional authentication for the shared connection

    Features from fast-channels:

    - FastAPI ASGI integration
    - fast-channels channel layer support (Redis, in-memory, etc.)
    - WebSocket lifecycle management
    - High-performance async operation
    """

    channel_layer_alias: str
    get_channel_layer = get_channel_layer  # type: ignore[assignment, unused-ignore]
