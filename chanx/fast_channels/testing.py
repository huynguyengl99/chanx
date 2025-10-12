"""
FastAPI fast-channels integration for Chanx WebSocket testing.

This module provides fast-channels-specific WebSocket testing utilities,
combining Chanx's testing mixin with fast-channels' WebSocket communicator
for comprehensive testing of FastAPI WebSocket consumers.
"""

from typing import Any

from chanx.core.testing import WebsocketCommunicatorMixin
from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
from fast_channels.testing import (
    WebsocketCommunicator as FastChannelsWebsocketCommunicator,
)


class WebsocketCommunicator(
    WebsocketCommunicatorMixin, FastChannelsWebsocketCommunicator
):
    """
    Fast-channels WebSocket communicator for testing Chanx consumers.

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
    """

    application: Any
    consumer: type[AsyncJsonWebsocketConsumer]
