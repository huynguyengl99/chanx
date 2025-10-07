"""
Message types for the background jobs consumer.
"""

from typing import Any, Literal

from chanx.messages.base import BaseMessage
from pydantic import BaseModel


class JobPayload(BaseModel):
    type: str = "default"
    content: str


class JobMessage(BaseMessage):
    """Background job message."""

    action: Literal["job"] = "job"
    payload: JobPayload


class JobStatusMessage(BaseMessage):
    """Job status message."""

    action: Literal["job_status"] = "job_status"
    payload: dict[str, Any]


class JobResult(BaseMessage):
    """Background job message."""

    action: Literal["job_result"] = "job_result"
    payload: Any
