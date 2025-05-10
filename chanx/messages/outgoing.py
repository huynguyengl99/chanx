"""
Standard outgoing message types for Chanx websockets.

Provides ready-to-use message types for server-to-client communication:
- PongMessage: Response to ping requests
- ErrorMessage: Communicates errors to clients
- AuthenticationMessage: Informs clients about authentication results
- CompleteMessage: Signals completion of message processing
- GroupCompleteMessage: Signals completion of group message distribution

These messages handle common communication patterns in WebSocket applications
including status updates, error reporting, and process completion signals.
"""

from typing import Any, Literal

from pydantic import BaseModel

from chanx.messages.base import BaseMessage


class PongMessage(BaseMessage):
    """
    Simple pong message to verify connection status.

    Used as a reply to ping messages to confirm that the connection is alive.
    """

    action: Literal["pong"] = "pong"
    payload: None = None


class ErrorMessage(BaseMessage):
    """
    Error message for communicating issues to the client.

    Contains error details in the payload field.

    Attributes:
        payload: Error information (typically includes a 'detail' field)
    """

    action: Literal["error"] = "error"
    payload: Any = None


class AuthenticationPayload(BaseModel):
    """
    Payload for authentication messages.

    Contains status information about the authentication process.

    Attributes:
        status_code: HTTP-like status code (e.g., 200 for success)
        status_text: Human-readable status description
        data: Additional authentication data
    """

    status_code: int
    status_text: str
    data: Any = None


class AuthenticationMessage(BaseMessage):
    """
    Authentication result message sent to the client.

    Sent after connection authentication to inform client of the result.

    Attributes:
        payload: AuthenticationPayload containing status details
    """

    action: Literal["authentication"] = "authentication"
    payload: AuthenticationPayload


# Constant for complete action type
ACTION_COMPLETE: Literal["complete"] = "complete"


class CompleteMessage(BaseMessage):
    """
    Confirmation message indicating processing is complete.

    Sent after a request has been fully processed to signal completion.
    """

    action: Literal["complete"] = ACTION_COMPLETE
    payload: None = None


GROUP_ACTION_COMPLETE: Literal["group_complete"] = "group_complete"


class GroupCompleteMessage(BaseMessage):
    """
    Confirmation message indicating group message processing is complete.

    Sent after a group message has been fully processed and distributed to all
    consumers in the group to signal completion of the group broadcast operation.
    This allows clients to know when all intended recipients have received the message.

    Attributes:
        action: Literal string 'group_complete' as the discriminator value
    """

    action: Literal["group_complete"] = GROUP_ACTION_COMPLETE
    payload: None = None
