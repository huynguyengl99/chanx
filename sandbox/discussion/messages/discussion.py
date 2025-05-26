from typing import Literal

from chanx.messages.base import (
    BaseChannelEvent,
    BaseGroupMessage,
    BaseMessage,
)
from chanx.messages.incoming import PingMessage
from pydantic import BaseModel


class DiscussionMessagePayload(BaseModel):
    content: str
    raw: bool = False


class NewDiscussionMessage(BaseMessage):
    action: Literal["new_message"] = "new_message"
    payload: DiscussionMessagePayload


class ReplyMessage(BaseMessage):
    action: Literal["reply"] = "reply"
    payload: DiscussionMessagePayload


DiscussionIncomingMessage = NewDiscussionMessage | PingMessage


class DiscussionMemberMessage(BaseGroupMessage):
    action: Literal["member_message"] = "member_message"
    payload: DiscussionMessagePayload


DiscussionGroupMessage = DiscussionMemberMessage


class NotifyEvent(BaseChannelEvent):
    class Payload(BaseModel):
        content: str

    handler: Literal["notify_people"] = "notify_people"
    payload: Payload


DiscussionEvent = NotifyEvent
