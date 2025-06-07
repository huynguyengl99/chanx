"""
Standard incoming message types for Chanx websockets.

Provides ready-to-use message types for WebSocket communication:
- PingMessage: Simple connection status check message

"""

from typing import Literal

from chanx.messages.base import BaseMessage


class PingMessage(BaseMessage):
    """Simple ping message to check connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None
