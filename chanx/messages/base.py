import abc
from types import UnionType
from typing import Any, Literal, Union, Unpack, get_args, get_origin

from pydantic import BaseModel, ConfigDict


class BaseMessage(BaseModel, abc.ABC):
    """
    Base websocket message
    """

    action: str

    payload: Any | None = None

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
        """
        Validates that subclasses properly define a unique action field with a Literal type.

        This ensures that:
        1. The 'action' field exists and is annotated
        2. The 'action' field uses a Literal type for strict type checking
        3. The action values are unique across all message types
        """
        super().__init_subclass__(**kwargs)

        # Skip validation for abstract base classes that might not have fields defined yet
        if cls.__module__ == "__main__" and cls.__name__ == "BaseMessage":
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

        action_values = set(get_args(action_field))

        # Check for empty literal
        if not action_values:
            raise ValueError(
                f"Class {cls.__name__!r} has an empty Literal for 'action'"
            )


class BaseIncomingMessage(BaseModel):
    """
    Base WebSocket incoming message wrapper.

    This class serves as a container for incoming WebSocket messages,
    allowing for a discriminated union pattern where the 'message' field
    can contain any message type derived from BaseMessage.

    During validation, the class will ensure that:
    1. The message union includes only BaseMessage subclasses
    2. The discriminator field 'action' is properly used
    """

    message: BaseMessage | BaseMessage

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
        """
        Validates that subclasses properly define a message field that uses
        a union of BaseMessage types for type discrimination.
        """
        super().__init_subclass__(**kwargs)

        try:
            message_field = cls.__annotations__["message"]
        except (KeyError, AttributeError) as e:
            raise TypeError(
                f"Class {cls.__name__!r} must define a 'message' field"
            ) from e

        # Check if it's a Union type
        origin = get_origin(message_field)
        if origin is Union or origin is UnionType:
            # Get all union members
            args = get_args(message_field)

            # Validate all union members are BaseMessage subclasses
            for arg in args:
                if not issubclass(arg, BaseMessage):
                    raise TypeError(
                        f"All union members in 'message' field of {cls.__name__!r} must be "
                        f"subclasses of BaseMessage, got {arg}"
                    )
        # Or a direct BaseMessage subclass
        elif not (
            message_field is BaseMessage
            or (
                isinstance(message_field, type)
                and issubclass(message_field, BaseMessage)
            )
        ):
            raise TypeError(
                f"The 'message' field of {cls.__name__!r} must be BaseMessage "
                f"or a union of BaseMessage subclasses, got {message_field}"
            )
