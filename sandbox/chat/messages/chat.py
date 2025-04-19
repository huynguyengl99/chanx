from typing import Literal

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.messages.incoming import PingMessage
from pydantic import BaseModel


class MessagePayload(BaseModel):
    content: str


class NewChatMessage(BaseMessage):
    action: Literal["new_chat_message"] = "new_chat_message"
    payload: MessagePayload


class ReplyChatMessage(BaseMessage):
    action: Literal["reply_chat_message"] = "reply_chat_message"
    payload: MessagePayload


class ChatIncomingMessage(BaseIncomingMessage):
    message: NewChatMessage | PingMessage
