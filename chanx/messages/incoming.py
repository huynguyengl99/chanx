from typing import Literal

from pydantic import BaseModel, Field

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.settings import chanx_settings


class PingMessage(BaseMessage):
    """Simple ping message to check connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None


class NewMessagePayload(BaseModel):
    message: str


class NewMessage(BaseMessage):
    """Send a new text message to the WebSocket server."""

    action: Literal["new_message"] = "new_message"
    payload: NewMessagePayload


class IncomingMessage(BaseIncomingMessage):
    message: PingMessage | NewMessage = Field(
        discriminator=chanx_settings.MESSAGE_ACTION_KEY
    )
