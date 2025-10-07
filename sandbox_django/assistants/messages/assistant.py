from typing import Any, Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


# Payloads
class StreamingPayload(BaseModel):
    content: str
    is_complete: bool = False
    message_id: int


class ErrorPayload(BaseModel):
    content: str
    message_id: str


class MessagePayload(BaseModel):
    content: str


# Outgoing group messages (WebSocket → Client)
class StreamingMessage(BaseMessage):
    """Streaming message chunk from assistant."""

    action: Literal["streaming"] = "streaming"
    payload: StreamingPayload


class CompleteStreamingMessage(BaseMessage):
    """Streaming message chunk from assistant."""

    action: Literal["complete_streaming"] = "complete_streaming"
    payload: StreamingPayload


class NewAssistantMessage(BaseMessage):
    """New assistant message (user or AI)."""

    action: Literal["new_assistant_message"] = "new_assistant_message"
    payload: dict[str, Any]


class AssistantErrorMessage(BaseMessage):
    """Error message from assistant."""

    action: Literal["assistant_error"] = "assistant_error"
    payload: ErrorPayload


# Channel events (Task → Consumer)
class StreamingEvent(BaseMessage):
    """Channel event for streaming chunks."""

    action: Literal["handle_streaming"] = "handle_streaming"
    payload: StreamingPayload


class CompleteStreamingEvent(BaseMessage):
    """Channel event for streaming chunks."""

    action: Literal["handle_complete_streaming"] = "handle_complete_streaming"
    payload: StreamingPayload


class NewAssistantMessageEvent(BaseMessage):
    """Channel event for new assistant messages."""

    action: Literal["handle_new_assistant_message"] = "handle_new_assistant_message"
    payload: dict[str, Any]


class ErrorEvent(BaseMessage):
    """Channel event for errors."""

    action: Literal["handle_error"] = "handle_error"
    payload: ErrorPayload


AssistantEvent = (
    StreamingEvent | CompleteStreamingEvent | NewAssistantMessageEvent | ErrorEvent
)
