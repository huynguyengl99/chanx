"""Messages for the topic demo."""

from typing import Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


class PostPayload(BaseModel):
    body: str
    author: str = "anonymous"


class PostMessage(BaseMessage):
    """Post something to a room."""

    action: Literal["post"] = "post"
    payload: PostPayload


class EchoMessage(BaseMessage):
    """Ask for an acknowledgement without broadcasting."""

    action: Literal["echo"] = "echo"
    payload: PostPayload


class PostedMessage(BaseMessage):
    """Confirm a post."""

    action: Literal["posted"] = "posted"
    payload: PostPayload


class RoomEvent(BaseMessage):
    """Something happened in a room."""

    action: Literal["room_event"] = "room_event"
    payload: PostPayload


class PresencePayload(BaseModel):
    user: str
    online: bool


class PresenceChanged(BaseMessage):
    """A user's presence changed."""

    action: Literal["presence_changed"] = "presence_changed"
    payload: PresencePayload
