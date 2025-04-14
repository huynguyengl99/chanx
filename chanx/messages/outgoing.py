from typing import Any, Literal

from chanx.messages.base import BaseMessage


class ErrorMessage(BaseMessage):
    """Send error message back to the user."""

    action: Literal["error"] = "error"
    payload: Any


ACTION_COMPLETE: Literal["complete"] = "complete"


class CompleteMessage(BaseMessage):
    """Acknowledge all the message has been sent."""

    action: Literal["complete"] = ACTION_COMPLETE
