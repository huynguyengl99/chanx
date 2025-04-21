"""
Standard incoming message types for Chanx websockets.

This module defines the base incoming message types and schemas used
for validating and processing messages received from clients.
Applications can extend these base types to add custom message handling.
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
    Default implementation of BaseIncomingMessage.

    Provides a concrete incoming message container with support for PingMessage type.
    Applications should extend this class to add support for additional message types.

    Attributes:
      message: The wrapped message object, using action as discriminator field
    """

    message: PingMessage = Field(discriminator=chanx_settings.MESSAGE_ACTION_KEY)
