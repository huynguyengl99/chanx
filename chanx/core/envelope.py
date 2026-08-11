"""
The routing metadata that travels alongside a message on the same flat frame.

Kept apart from both the consumer and the topic so each can import it without the
two importing each other.
"""

from contextvars import ContextVar
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from chanx.constants import ENVELOPE_FIELDS, ENVELOPE_VERSION

TOPIC_EVENT_TYPE = "handle_topic_event"

# Set while a frame is being handled, so replies carry its ref and pushed events
# carry their seq.
current_ref: ContextVar[str | None] = ContextVar("chanx_current_ref", default=None)
current_seq: ContextVar[int | None] = ContextVar("chanx_current_seq", default=None)


class Envelope(BaseModel):
    """Routing metadata carried alongside a message on the same flat frame."""

    version: int = ENVELOPE_VERSION
    topic: str | None = None
    ref: str | None = None
    seq: int | None = None


class TopicErrorReason(StrEnum):
    """Why a topic-addressed frame could not be served."""

    UNKNOWN_TOPIC = "unknown_topic"
    UNAUTHORIZED = "unauthorized"
    NOT_SUBSCRIBED = "not_subscribed"


def strip_envelope(content: dict[str, Any]) -> dict[str, Any]:
    """Drop reserved keys so the rest validates as a plain Chanx message."""
    return {k: v for k, v in content.items() if k not in ENVELOPE_FIELDS}
