import abc
from types import UnionType
from typing import (
    Any,
    ClassVar,
    Literal,
    TypeVar,
    Union,
    Unpack,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict, Field


class BaseMessage(BaseModel, abc.ABC):
    """
    Base websocket message.

    All message types should inherit from this class and define
    a unique 'action' field using a Literal type.

    Attributes:
        action: Discriminator field identifying message type
        payload: Optional message payload data
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


# TypeVar for the message base class type
T = TypeVar("T", bound=BaseMessage)


class MessageContainerMixin(BaseModel, abc.ABC):
    """
    Mixin for message container classes that wrap a message type.

    This mixin provides common validation logic for classes that contain
    a field with a union of message types using a discriminator.

    Attributes:
        _message_field_name: Name of the field containing the message
        _message_base_class: Base class that all message types must inherit from
    """

    _message_field_name: ClassVar[str]
    _message_base_class: ClassVar[type[BaseMessage]]

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
        """
        Validates that subclasses properly define a message field that uses
        a union of specified base message types for type discrimination.

        Args:
            **kwargs: Configuration options for Pydantic model

        Raises:
            TypeError: If required message field is missing or not of correct type
        """
        super().__init_subclass__(**kwargs)

        field_name = cls._message_field_name
        base_class = cls._message_base_class

        try:
            message_field = cls.__annotations__[field_name]
        except (KeyError, AttributeError) as e:
            raise TypeError(
                f"Class {cls.__name__!r} must define a '{field_name}' field"
            ) from e

        # Check if it's a Union type
        origin = get_origin(message_field)
        if origin is Union or origin is UnionType:
            # Get all union members
            args = get_args(message_field)

            # Validate all union members are correct base class subclasses
            for arg in args:
                if not issubclass(arg, base_class):
                    raise TypeError(
                        f"All union members in '{field_name}' field of {cls.__name__!r} must be "
                        f"subclasses of {base_class.__name__}, got {arg}"
                    )
        # Or a direct subclass of the base class
        elif not (
            message_field is base_class
            or (
                isinstance(message_field, type)
                and issubclass(message_field, base_class)
            )
        ):
            raise TypeError(
                f"The '{field_name}' field of {cls.__name__!r} must be {base_class.__name__} "
                f"or a union of {base_class.__name__} subclasses, got {message_field}"
            )

        # Check if discriminator is already explicitly set
        has_discriminator = False
        if (
            hasattr(cls, field_name)
            and getattr(getattr(cls, field_name, None), "discriminator", None)
            is not None
        ):
            has_discriminator = True

        # Add discriminator automatically if not explicitly set
        if not has_discriminator:
            # Check if there's a settings module with MESSAGE_ACTION_KEY
            from chanx.settings import chanx_settings

            # Update the field with discriminator
            cls.model_fields[field_name] = Field(
                discriminator=chanx_settings.MESSAGE_ACTION_KEY
            )


class BaseIncomingMessage(MessageContainerMixin):
    """
    Base WebSocket incoming message wrapper.

    This class serves as a container for incoming WebSocket messages,
    allowing for a discriminated union pattern where the 'message' field
    can contain any message type derived from BaseMessage.

    Attributes:
        message: The wrapped message object, using action as discriminator field
    """

    _message_field_name: ClassVar[str] = "message"
    _message_base_class: ClassVar[type[BaseMessage]] = BaseMessage

    message: BaseMessage


class BaseOutgoingGroupMessage(MessageContainerMixin):
    """
    Base WebSocket outgoing group message wrapper.

    Similar to BaseIncomingMessage, but for group messages being sent out.

    Attributes:
        group_message: The wrapped group message
    """

    _message_field_name: ClassVar[str] = "group_message"
    _message_base_class: ClassVar[type[BaseMessage]] = BaseGroupMessage

    group_message: BaseGroupMessage
