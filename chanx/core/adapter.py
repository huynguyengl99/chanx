# mypy: disable-error-code=assignment
"""
Framework adapter for Django Channels and Fast-Channels compatibility.

This module provides a unified interface for using Chanx with either Django Channels
or Fast-Channels depending on the runtime environment. It automatically detects
which framework is available and imports the appropriate implementations.
"""

from .check import IS_USING_DJANGO

if IS_USING_DJANGO:
    from channels.generic.websocket import AsyncJsonWebsocketConsumer
    from channels.layers import BaseChannelLayer, get_channel_layer
    from channels.testing import WebsocketCommunicator

    from asgiref.typing import WebSocketConnectEvent, WebSocketDisconnectEvent

else:
    from fast_channels.consumer import AsyncJsonWebsocketConsumer
    from fast_channels.layers import get_channel_layer
    from fast_channels.layers.base import BaseChannelLayer
    from fast_channels.testing import WebsocketCommunicator
    from fast_channels.type_defs import WebSocketConnectEvent, WebSocketDisconnectEvent

__all__ = [
    "get_channel_layer",
    "AsyncJsonWebsocketConsumer",
    "WebSocketDisconnectEvent",
    "WebSocketConnectEvent",
    "WebsocketCommunicator",
    "BaseChannelLayer",
]
