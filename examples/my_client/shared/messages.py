from typing import Literal

from pydantic import BaseModel


class ChatPayload(BaseModel):
    """ChatPayload"""

    message: str


class ChatNotificationMessage(BaseModel):
    """Chat notification message."""

    action: Literal["chat_notification"] = "chat_notification"
    payload: ChatPayload


class PingMessage(BaseModel):
    """Simple ping message to check WebSocket connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None


class PongMessage(BaseModel):
    """Simple pong message response to ping requests."""

    action: Literal["pong"] = "pong"
    payload: None = None
