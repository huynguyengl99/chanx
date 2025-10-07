"""
Message types for the system chat consumer.
"""

from typing import Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str


class UserMessage(BaseMessage):
    """System message for direct communication."""

    action: Literal["user_message"] = "user_message"
    payload: MessagePayload


class SystemEchoMessage(BaseMessage):
    """System echo response message."""

    action: Literal["system_echo"] = "system_echo"
    payload: MessagePayload
