from typing import Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


# Common base payloads
class VotePayload(BaseModel):
    """Base payload for vote-related operations."""

    target_type: Literal["topic", "reply"]  # What we're voting on
    target_id: int  # ID of topic or reply
    vote_count: int  # Current vote count


# Common base messages
class VoteUpdatedMessage(BaseMessage):
    """Broadcast when votes are updated."""

    action: Literal["vote_updated"] = "vote_updated"
    payload: VotePayload


# Common channel events
class VoteUpdateEvent(BaseMessage):
    """Channel event for vote updates."""

    action: Literal["update_vote"] = "update_vote"
    payload: VotePayload
