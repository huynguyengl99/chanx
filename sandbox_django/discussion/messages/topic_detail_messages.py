from typing import Any, Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel

from .common_messages import (
    VoteUpdateEvent,
)


# Payloads for topic detail view message types
class NewReplyEventPayload(BaseModel):
    """Payload for new reply channel events."""

    id: int
    content: str
    author: dict[str, Any]
    vote_count: int
    is_accepted: bool
    created_at: str
    formatted_created_at: str
    topic_id: int
    topic_title: str


class AnswerAcceptedEventPayload(BaseModel):
    """Payload for answer accepted events."""

    topic_id: int
    topic_title: str
    reply_id: int
    reply_author: str


class AnswerUnacceptedEventPayload(BaseModel):
    """Payload for answer unaccepted events."""

    topic_id: int
    topic_title: str
    reply_id: int
    reply_author: str


# Outgoing group messages for topic detail view
class ReplyCreatedMessage(BaseMessage):
    """Broadcast when a new reply is created."""

    action: Literal["reply_created"] = "reply_created"
    payload: NewReplyEventPayload


class AnswerAcceptedMessage(BaseMessage):
    """Broadcast when an answer is accepted."""

    action: Literal["answer_accepted"] = "answer_accepted"
    payload: AnswerAcceptedEventPayload


class AnswerUnacceptedMessage(BaseMessage):
    """Broadcast when an answer is unaccepted."""

    action: Literal["answer_unaccepted"] = "answer_unaccepted"
    payload: AnswerUnacceptedEventPayload


# Channel events for topic detail view
class NewReplyEvent(BaseMessage):
    """Channel event for new reply creation."""

    action: Literal["handle_new_reply"] = "handle_new_reply"
    payload: NewReplyEventPayload


class AnswerAcceptedEvent(BaseMessage):
    """Channel event for answer acceptance."""

    action: Literal["handle_answer_accepted"] = "handle_answer_accepted"
    payload: AnswerAcceptedEventPayload


class AnswerUnacceptedEvent(BaseMessage):
    """Channel event for answer unacceptance."""

    action: Literal["handle_answer_unaccepted"] = "handle_answer_unaccepted"
    payload: AnswerUnacceptedEventPayload


# Union of all channel events for topic detail view
TopicDetailEvent = (
    NewReplyEvent | AnswerAcceptedEvent | AnswerUnacceptedEvent | VoteUpdateEvent
)
