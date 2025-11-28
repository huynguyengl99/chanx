from typing import Literal

from pydantic import BaseModel

from ..shared.messages import (
    ChatNotificationMessage,
    ChatPayload,
    PingMessage,
    PongMessage,
)


class ChatMessage(BaseModel):
    """Chat message for the basic chat consumer."""

    action: Literal["chat"] = "chat"
    payload: ChatPayload


IncomingMessage = ChatNotificationMessage | PongMessage
OutgoingMessage = ChatMessage | PingMessage
