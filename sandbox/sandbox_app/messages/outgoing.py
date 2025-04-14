from typing import Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


class PongMessage(BaseMessage):
    """Simple ping speech message to check connection status."""

    action: Literal["pong"] = "pong"


class ReplyPayload(BaseModel):
    message: str


class ReplyMessage(BaseMessage):
    """Send a new speech message to the WebSocket server."""

    action: Literal["reply"] = "reply"
    payload: ReplyPayload
