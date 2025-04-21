from typing import Literal

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.messages.incoming import PingMessage
from pydantic import BaseModel


class MessagePayload(BaseModel):
    content: str
    groups: list[str] | None = None


class NewChatMessage(BaseMessage):
    action: Literal["new_chat_message"] = "new_chat_message"
    payload: MessagePayload


class ReplyChatMessage(BaseMessage):
    action: Literal["reply_chat_message"] = "reply_chat_message"
    payload: MessagePayload


class JoinGroupPayload(BaseModel):
    group_name: str


class JoinGroupMessage(BaseMessage):
    action: Literal["join_group"] = "join_group"
    payload: JoinGroupPayload


class ChatIncomingMessage(BaseIncomingMessage):
    message: NewChatMessage | PingMessage | JoinGroupMessage
