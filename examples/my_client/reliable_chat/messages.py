from typing import Literal

from pydantic import BaseModel

from ..shared.messages import (
    ChatNotificationMessage,
    PingMessage,
    PongMessage,
)


class ReliableChatPayload(BaseModel):
    """ReliableChatPayload"""

    message: str


class ReliableChatMessage(BaseModel):
    """Reliable chat message."""

    action: Literal["reliable_chat"] = "reliable_chat"
    payload: ReliableChatPayload


class ReliableChatNotificationMessage(BaseModel):
    """Reliable chat notification message."""

    action: Literal["reliable_chat_notification"] = "reliable_chat_notification"
    payload: ReliableChatPayload


IncomingMessage = (
    PongMessage | ReliableChatNotificationMessage | ChatNotificationMessage
)
OutgoingMessage = PingMessage | ReliableChatMessage
