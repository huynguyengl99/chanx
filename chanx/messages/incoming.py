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

from pydantic import Field

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.settings import chanx_settings


class PingMessage(BaseMessage):
    """Simple ping message to check connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None


class IncomingMessage(BaseIncomingMessage):
    """
    Ready-to-use implementation of BaseIncomingMessage.

    Provides a concrete incoming message container with support for PingMessage only.
    Can be used directly for simple applications that only need ping functionality,
    or as a starting point for more complex implementations.

    Attributes:
        message: The wrapped message object, using action as discriminator
    """

    message: PingMessage = Field(discriminator=chanx_settings.MESSAGE_ACTION_KEY)
