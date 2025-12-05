from typing import Any, Literal

from pydantic import BaseModel

from ..shared.messages import PingMessage, PongMessage


class AnalyticsPayload(BaseModel):
    """AnalyticsPayload"""

    event: str
    data: Any | None = None


class AnalyticsMessage(BaseModel):
    """Analytics message."""

    action: Literal["analytics"] = "analytics"
    payload: AnalyticsPayload


class AnalyticsNotificationMessage(BaseModel):
    """Analytics notification message."""

    action: Literal["analytics_notification"] = "analytics_notification"
    payload: AnalyticsPayload


IncomingMessage = AnalyticsNotificationMessage | PongMessage
OutgoingMessage = AnalyticsMessage | PingMessage
