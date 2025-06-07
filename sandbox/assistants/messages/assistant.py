from typing import Literal

from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from pydantic import BaseModel


class MessagePayload(BaseModel):
    content: str


class NewMessage(BaseMessage):
    """
    New message for assistant.
    """

    action: Literal["new_message"] = "new_message"
    payload: MessagePayload


class ReplyMessage(BaseMessage):
    action: Literal["reply"] = "reply"
    payload: MessagePayload


class StreamingMessage(BaseMessage):
    """
    Streaming message of assistant.
    """

    action: Literal["streaming"] = "streaming"
    payload: MessagePayload


class StreamingReplyMessage(BaseMessage):
    """
    Streaming reply message of assistant.
    """

    class Payload(BaseModel):
        id: str
        content: str

    action: Literal["streaming_reply"] = "streaming_reply"
    payload: Payload


class StreamingReplyCompleteMessage(BaseMessage):
    """
    Streaming reply message of assistant.
    """

    class Payload(BaseModel):
        id: str

    action: Literal["streaming_reply_complete"] = "streaming_reply_complete"
    payload: Payload


AssistantIncomingMessage = NewMessage | PingMessage | StreamingMessage
