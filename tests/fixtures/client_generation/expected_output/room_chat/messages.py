from typing import Literal

from pydantic import BaseModel

from ..shared.messages import PingMessage, PongMessage


class RoomMessagePayload(BaseModel):
    """RoomMessagePayload"""

    message: str
    room_name: str | None = None
    status: Literal["PENDING", "DELIVERED", "FAILED"] = "PENDING"


class RoomChatMessage(BaseModel):
    """Room chat message."""

    action: Literal["room_chat"] = "room_chat"
    payload: RoomMessagePayload


class RoomNotificationMessage(BaseModel):
    """Room notification message."""

    action: Literal["room_notification"] = "room_notification"
    payload: RoomMessagePayload


IncomingMessage = PongMessage | RoomNotificationMessage
OutgoingMessage = PingMessage | RoomChatMessage
