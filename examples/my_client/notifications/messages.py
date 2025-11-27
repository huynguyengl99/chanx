from typing import Literal

from pydantic import BaseModel

from ..shared.messages import PingMessage, PongMessage


class NotificationPayload(BaseModel):
    """NotificationPayload"""

    type: str = "user"
    message: str


class NotificationBroadcastMessage(BaseModel):
    """Notification broadcast message."""

    action: Literal["notification_broadcast"] = "notification_broadcast"
    payload: NotificationPayload


class NotificationMessage(BaseModel):
    """Notification message."""

    action: Literal["notification"] = "notification"
    payload: NotificationPayload


IncomingMessage = NotificationBroadcastMessage | PongMessage
OutgoingMessage = NotificationMessage | PingMessage
