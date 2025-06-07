"""
Base message types and containers for Chanx WebSocket communication.

This module defines the foundational message structure for the Chanx WebSocket framework,
providing a type-safe, validated message system built on Pydantic. The architecture
uses discriminated unions to enable type-safe message handling with runtime validation.

Key components:
- BaseMessage: Abstract base class for all message types with action discriminator
- BaseGroupMessage: Extends base messages with group-specific metadata
- BaseChannelEvent: Base class for typed channel layer events

The message system enforces that all concrete message types must define a unique 'action'
field using a Literal type, which serves as the discriminator for message type identification.
This enables both static type checking and runtime validation of message structures.

Message containers use Pydantic's discriminated union pattern to automatically deserialize
JSON messages into the correct message type based on the 'action' field.

Channel events provide a separate communication channel through the Django Channels layer,
allowing consumers to send typed messages to each other outside of the WebSocket connection.
Each event type must define a unique 'handler' field.
"""

import abc
from typing import Any, Literal, get_origin

from pydantic import BaseModel, ConfigDict
from typing_extensions import Unpack


class BaseMessage(BaseModel, abc.ABC):
    """
    Base websocket message.

    All message types should inherit from this class and define
    a unique 'action' field using a Literal type.

    Attributes:
        action: Discriminator field identifying message type
        payload: Optional message payload data
    """

    action: Any
    payload: Any

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
        """
        Validates that subclasses properly define a unique action field with a Literal type.

        This ensures that:
        1. The 'action' field exists and is annotated
        2. The 'action' field uses a Literal type for strict type checking
        3. The action values are unique across all message types

        Args:
            **kwargs: Configuration options for Pydantic model

        Raises:
            TypeError: If action field is missing or not a Literal type
        """
        super().__init_subclass__(**kwargs)

        if abc.ABC in cls.__bases__:
            return

        try:
            action_field = cls.__annotations__["action"]
        except (KeyError, AttributeError) as e:
            raise TypeError(
                f"Class {cls.__name__!r} must define an 'action' field"
            ) from e

        if get_origin(action_field) is not Literal:
            raise TypeError(
                f"Class {cls.__name__!r} requires the field 'action' to be a `Literal` type"
            )


class BaseGroupMessage(BaseMessage, abc.ABC):
    """
    Base message for group broadcasting.

    Extends BaseMessage with properties to indicate message's relationship
    to the current user and connection.

    Attributes:
        is_mine: Whether message was sent by the current user
        is_current: Whether message was sent by the current connection
    """

    is_mine: bool = False
    is_current: bool = False


class BaseChannelEvent(BaseModel, abc.ABC):
    """
    Base class for typed channel events.

    Channel events provide a way to send typed messages through the channel layer
    to specific consumer methods. Each event type must define a unique 'handler'
    field that corresponds to a method name on the target consumer.

    Attributes:
        handler: Method name on the consumer that will handle this event
        payload: Event-specific data payload
    """

    handler: Any
    payload: Any
