"""
Type definitions for Chanx websocket components.

This module provides TypedDict and other type definitions that represent
the structure of complex objects used throughout the Chanx framework.
"""

from collections.abc import Awaitable, Callable
from types import UnionType
from typing import Any, Literal, TypeAlias, TypedDict

from chanx.messages.base import BaseMessage


class HandlerInfo(TypedDict):
    """Information stored on handler functions by the @ws_handler decorator."""

    action: str
    message_action: str
    input_type: type[BaseMessage] | None
    output_type: (
        type[BaseMessage]
        | UnionType
        | list[type[BaseMessage]]
        | tuple[type[BaseMessage], ...]
        | None
    )
    method_name: str


class AsyncAPIHandlerInfo(HandlerInfo, total=False):
    """Extended handler info with AsyncAPI metadata."""

    description: str | None
    summary: str | None
    tags: list[str] | None
    consumer_name: str


class ChannelInfo(TypedDict, total=False):
    """Information stored on consumer classes by the @channel decorator."""

    name: str | None
    description: str | None
    tags: list[str] | None


class GroupMessageEvent(TypedDict):
    """
    Type definition for group message events.

    Represents the structure of events sent to group members through
    the channel layer.

    Attributes:
        message: The message content to be sent
        kind: Type of content format ('json' or 'message')
        exclude_current: Whether to exclude the sender from receiving the message
        from_channel: Channel name of the sender
    """

    message: dict[str, Any]
    kind: Literal["json", "message"]
    exclude_current: bool
    from_channel: str


class EventPayload(TypedDict):
    """
    Channel layer message containing event data.

    Attributes:
        event_data: Serialized event data dictionary
    """

    event_data: dict[str, Any]


SendMessageFn: TypeAlias = Callable[[BaseMessage], Awaitable[None]]
