from typing import Literal

from pydantic import BaseModel


class EchoMessage(BaseModel):
    """Message asking the echo consumer to repeat something."""

    action: Literal["echo"] = "echo"
    payload: str


class EchoReplyMessage(BaseModel):
    """The echo consumer's reply."""

    action: Literal["echo_reply"] = "echo_reply"
    payload: str


IncomingMessage = EchoReplyMessage
OutgoingMessage = EchoMessage
