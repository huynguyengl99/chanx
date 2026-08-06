"""
Django Channels concrete WebSocket demultiplexer implementation.

This module provides the concrete AsyncJsonWebsocketDemultiplexer class that
combines Chanx's multiplexing functionality (from the core mixin) with Django
Channels' AsyncJsonWebsocketConsumer base class. This is the class users should
import to serve several consumers over a single route with Django and Channels.

The concrete demultiplexer inherits from both:
- chanx.core.multiplex.ChanxDemultiplexerMixin (Chanx mixin with all features)
- channels.generic.websocket.AsyncJsonWebsocketConsumer (Django Channels base)
"""

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as ChannelsAsyncJsonWebsocketConsumer,
)
from channels.layers import get_channel_layer

from typing_extensions import TypeVar

from chanx.core.multiplex import ChanxDemultiplexerMixin
from chanx.messages.base import BaseMessage

ReceiveEvent = TypeVar("ReceiveEvent", bound=BaseMessage, default=BaseMessage)


class AsyncJsonWebsocketDemultiplexer(  # type: ignore[misc]
    ChanxDemultiplexerMixin[ReceiveEvent], ChannelsAsyncJsonWebsocketConsumer
):
    """
    Django Channels WebSocket demultiplexer with Chanx enhanced features.

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
    - Built-in authentication for the shared connection

    Features from Django Channels:

    - Django ASGI integration
    - Django channel layer support (Redis, in-memory, etc.)
    - Django authentication and session support
    - WebSocket lifecycle management
    """

    get_channel_layer = get_channel_layer  # type: ignore[assignment, unused-ignore]
