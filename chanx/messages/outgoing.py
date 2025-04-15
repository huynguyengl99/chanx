from typing import Any, Literal

from pydantic import BaseModel

from chanx.messages.base import BaseMessage


class PongMessage(BaseMessage):
    """Simple ping speech message to check connection status."""

    action: Literal["pong"] = "pong"


class ErrorMessage(BaseMessage):
    """Send error message back to the user."""

    action: Literal["error"] = "error"
    payload: Any


class AuthenticationPayload(BaseModel):
    status_code: int
    data: Any = None


class AuthenticationMessage(BaseMessage):
    """Send error message back to the user."""

    action: Literal["authentication"] = "authentication"
    payload: AuthenticationPayload


ACTION_COMPLETE: Literal["complete"] = "complete"


class CompleteMessage(BaseMessage):
    """Acknowledge all the message has been sent."""

    action: Literal["complete"] = ACTION_COMPLETE
