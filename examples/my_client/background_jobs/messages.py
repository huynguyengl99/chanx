from typing import Literal

from pydantic import BaseModel

from ..shared.messages import PingMessage, PongMessage


class JobPayload(BaseModel):
    """JobPayload"""

    type: str = "default"
    content: str


class JobMessage(BaseModel):
    """Background job message."""

    action: Literal["job"] = "job"
    payload: JobPayload


class JobStatusMessage(BaseModel):
    """Job status message."""

    action: Literal["job_status"] = "job_status"
    payload: dict


IncomingMessage = JobStatusMessage | PongMessage
OutgoingMessage = JobMessage | PingMessage
