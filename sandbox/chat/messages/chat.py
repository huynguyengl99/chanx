from typing import Literal

from chanx.messages.base import BaseMessage
from chanx.messages.incoming import IncomingMessage, PingMessage
from pydantic import BaseModel


class MessagePayload(BaseModel):
    content: str


class NewMessage(BaseMessage):
    action: Literal["new_message"] = "new_message"
    payload: MessagePayload


class ReplyMessage(BaseMessage):
    action: Literal["reply"] = "reply"
    payload: MessagePayload


class ChatIncomingMessage(IncomingMessage):
    message: NewMessage | PingMessage
