"""
Message types for the room chat consumer.
"""

from typing import Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


class RoomMessagePayload(BaseModel):
    message: str
    room_name: str | None = None


class RoomChatMessage(BaseMessage):
    """Room chat message."""

    action: Literal["room_chat"] = "room_chat"
    payload: RoomMessagePayload


class RoomNotificationMessage(BaseMessage):
    """Room notification message."""

    action: Literal["room_notification"] = "room_notification"
    payload: RoomMessagePayload
