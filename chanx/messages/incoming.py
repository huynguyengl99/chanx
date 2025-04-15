from typing import Literal

from pydantic import Field

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.settings import chanx_settings


class PingMessage(BaseMessage):
    """Simple ping message to check connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None


class IncomingMessage(BaseIncomingMessage):
    message: PingMessage = Field(discriminator=chanx_settings.MESSAGE_ACTION_KEY)
