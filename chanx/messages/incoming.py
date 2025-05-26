"""
Standard incoming message types for Chanx websockets.

Provides ready-to-use message types for WebSocket communication:
- PingMessage: Simple connection status check message
- IncomingMessage: Basic schema implementation that supports PingMessage

For real applications, you can use IncomingMessage directly for simple cases,
or extend BaseIncomingMessage with your own custom message types for more
complex applications. The IncomingMessage class only supports PingMessage.
"""

from typing import Literal

from chanx.messages.base import BaseMessage


class PingMessage(BaseMessage):
    """Simple ping message to check connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None


IncomingMessage = PingMessage
