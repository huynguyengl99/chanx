from typing import Literal

from pydantic import BaseModel


class ChatNotificationMessage(BaseModel):
    """Notification broadcast to the chat group."""

    action: Literal["chat_notification"] = "chat_notification"
    payload: str


IncomingMessage = ChatNotificationMessage
