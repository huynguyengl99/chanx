"""
Type definitions for Chanx websocket components.

This module provides TypedDict and other type definitions that represent
the structure of complex objects used throughout the Chanx framework.
"""

from typing import Any, Literal, TypedDict


class GroupMemberEvent(TypedDict):
    """
    Type definition for group member events.

    Represents the structure of events sent to group members through
    the channel layer.

    Attributes:
        content: The message content to be sent
        kind: Type of content format ('json' or 'message')
        exclude_current: Whether to exclude the sender from receiving the message
        from_channel: Channel name of the sender
        from_user_pk: User PK of the sender, if authenticated
    """

    content: dict[str, Any]
    kind: Literal["json", "message"]
    exclude_current: bool
    from_channel: str
    from_user_pk: int | None
