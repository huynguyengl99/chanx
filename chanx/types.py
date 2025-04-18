from typing import Any, Literal, TypedDict


class GroupMemberEvent(TypedDict):
    """
    Type definition for group member events.

    Represents the structure of events sent to group members through
    the channel layer.

    Attributes:
        type: Event type name (typically "send_group_member")
        content: The message content to be sent
        kind: Type of content format ('json' or 'message')
        exclude_current: Whether to exclude the sender from receiving the message
        from_channel: Channel name of the sender
        from_user_pk: User PK of the sender, if authenticated
    """

    type: str
    content: dict[str, Any]
    kind: Literal["json", "message"]
    exclude_current: bool
    from_channel: str
    from_user_pk: int | None
