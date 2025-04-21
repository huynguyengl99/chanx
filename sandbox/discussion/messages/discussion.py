from typing import Literal

from chanx.messages.base import BaseGroupMessage, BaseMessage, BaseOutgoingGroupMessage
from chanx.messages.incoming import IncomingMessage, PingMessage
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


class DiscussionIncomingMessage(IncomingMessage):
    message: NewDiscussionMessage | PingMessage


class DiscussionMemberMessage(BaseGroupMessage):
    action: Literal["member_message"] = "member_message"
    payload: DiscussionMessagePayload


class DiscussionGroupMessage(BaseOutgoingGroupMessage):
    group_message: DiscussionMemberMessage
