"""
FastAPI fast-channels integration for Chanx WebSocket testing.

This module provides fast-channels-specific WebSocket testing utilities,
combining Chanx's testing mixin with fast-channels' WebSocket communicator
for comprehensive testing of FastAPI WebSocket consumers.
"""

from typing import Any

from chanx.core.testing import WebsocketCommunicatorMixin
from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
from fast_channels.testing import WebsocketCommunicator


class FastChannelsWebsocketCommunicator(
    WebsocketCommunicatorMixin, WebsocketCommunicator
):
    """
    FastAPI fast-channels WebSocket communicator for testing Chanx consumers.

    Combines Chanx testing mixin features with fast-channels' WebSocket communicator,
    providing comprehensive testing capabilities for FastAPI applications:

    Chanx features (from WebsocketCommunicatorMixin):
    - Structured message sending/receiving with BaseMessage objects
    - Automatic message collection until completion signals
    - Message validation using consumer's type adapters
    - Async context manager support for automatic cleanup
    - send_message(): Send BaseMessage objects directly
    - receive_all_json(): Collect all messages until timeout
    - receive_all_messages(): Collect and validate messages until stop action

    FastAPI fast-channels features:
    - Full compatibility with FastAPI ASGI applications
    - fast-channels channel layer support
    - High-performance async operation

    Usage:
        ```python
        from chanx.fast_channels.testing import FastChannelsWebsocketCommunicator

        async def test_my_consumer():
            communicator = FastChannelsWebsocketCommunicator(
                application=my_app,
                path="/ws/chat/",
                consumer=MyChatConsumer
            )

            async with communicator:
                await communicator.send_message(PingMessage())
                messages = await communicator.receive_all_messages()
                assert len(messages) > 0
        ```

    Note:
        Unlike Django Channels integration, fast-channels does not have built-in
        authentication message handling. Authentication should be handled through
        FastAPI's dependency injection or custom middleware.
    """

    application: Any
    consumer: type[AsyncJsonWebsocketConsumer]


__all__ = ["FastChannelsWebsocketCommunicator"]
