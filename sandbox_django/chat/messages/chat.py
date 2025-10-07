from typing import Any, Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


class MemberAddedMessage(BaseMessage):
    action: Literal["member_added"] = "member_added"
    payload: dict[str, Any]


class NotifyMemberAddedEvent(BaseMessage):
    action: Literal["notify_member_added"] = "notify_member_added"
    payload: dict[str, Any]


class MemberRemovedPayload(BaseModel):
    user_pk: int
    email: str


class MemberRemovedMessage(BaseMessage):
    action: Literal["member_removed"] = "member_removed"
    payload: MemberRemovedPayload


class UserRemovedFromGroupMessage(BaseMessage):
    class Payload(BaseModel):
        redirect: str
        message: str

    action: Literal["user_removed_from_group"] = "user_removed_from_group"
    payload: Payload


class NotifyMemberRemovedEvent(BaseMessage):
    action: Literal["notify_member_removed"] = "notify_member_removed"
    payload: MemberRemovedPayload


class NewChatMessageEvent(BaseMessage):
    class Payload(BaseModel):
        message_data: dict[str, Any]
        user_pk: int | None

    action: Literal["new_chat_message"] = "new_chat_message"
    payload: Payload


ChatDetailEvent = (
    NotifyMemberAddedEvent | NotifyMemberRemovedEvent | NewChatMessageEvent
)
