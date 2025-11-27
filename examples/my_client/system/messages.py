from typing import Literal

from pydantic import BaseModel

from ..shared.messages import PingMessage, PongMessage


class MessagePayload(BaseModel):
    """MessagePayload"""

    message: str


class SystemEchoMessage(BaseModel):
    """System echo response message."""

    action: Literal["system_echo"] = "system_echo"
    payload: MessagePayload


class UserMessage(BaseModel):
    """System message for direct communication."""

    action: Literal["user_message"] = "user_message"
    payload: MessagePayload


IncomingMessage = PongMessage | SystemEchoMessage
OutgoingMessage = PingMessage | UserMessage
