"""
Base message types and containers for Chanx WebSocket communication.

This module defines the foundational message structure for the Chanx WebSocket framework,
providing a type-safe, validated message system built on Pydantic. The architecture
uses discriminated unions to enable type-safe message handling with runtime validation.

Key components:
- BaseMessage: Abstract base class for all message types with action discriminator

The message system enforces that all concrete message types must define a unique 'action'
field using a Literal type, which serves as the discriminator for message type identification.
This enables both static type checking and runtime validation of message structures.

Message containers use Pydantic's discriminated union pattern to automatically deserialize
JSON messages into the correct message type based on the 'action' field.
"""

import abc
from typing import Any, Literal, get_origin

from pydantic import BaseModel, ConfigDict
from typing_extensions import Unpack


class BaseMessage(BaseModel, abc.ABC):
    """
    Base message for all Chanx communications.

    Use cases:

    - Incoming messages: Client to server WebSocket communication
    - Outgoing messages: Server to client responses and notifications
    - Channel events: Server to server communication via channel layer

    All message types must define a unique 'action' field using a Literal type.
    Action values must be unique within each consumer for proper routing.

    Attributes:
        action: Discriminator field identifying message type
        payload: Message data
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

        if get_origin(action_field) is not Literal:  # type: ignore[comparison-overlap,unused-ignore]
            raise TypeError(
                f"Class {cls.__name__!r} requires the field 'action' to be a `Literal` type"
            )
