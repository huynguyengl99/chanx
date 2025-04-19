import abc
from types import UnionType
from typing import Any, Literal, Union, Unpack, get_args, get_origin

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


class BaseIncomingMessage(BaseModel):
    """
    Base WebSocket incoming message wrapper.

    This class serves as a container for incoming WebSocket messages,
    allowing for a discriminated union pattern where the 'message' field
    can contain any message type derived from BaseMessage.

    Attributes:
        message: The wrapped message object, using action as discriminator field

    During validation, the class will ensure that:
    1. The message union includes only BaseMessage subclasses
    2. The discriminator field 'action' is properly used
    """

    message: BaseMessage

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
        """
        Validates that subclasses properly define a message field that uses
        a union of BaseMessage types for type discrimination.

        Args:
            **kwargs: Configuration options for Pydantic model

        Raises:
            TypeError: If message field is missing or not a BaseMessage type/union
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

        has_discriminator_message_field = False
        if hasattr(cls, "message") and cls.message.discriminator is not None:  # type: ignore
            has_discriminator_message_field = True

        # Add discriminator automatically if not explicitly set
        if not has_discriminator_message_field:
            # Check if there's a settings module with MESSAGE_ACTION_KEY
            from chanx.settings import chanx_settings

            # Update the field with discriminator
            cls.model_fields["message"] = Field(
                discriminator=chanx_settings.MESSAGE_ACTION_KEY
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


class BaseOutgoingGroupMessage(BaseModel):
    """
    Base WebSocket outgoing group message wrapper.

    Similar to BaseIncomingMessage, but for group messages being sent out.

    Attributes:
        group_message: The wrapped group message
    """

    group_message: BaseGroupMessage

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
        """
        Validates that subclasses properly define a message field that uses
        a union of BaseGroupMessage types for type discrimination.

        Args:
            **kwargs: Configuration options for Pydantic model

        Raises:
            TypeError: If group_message field is missing or not a BaseGroupMessage type/union
        """
        super().__init_subclass__(**kwargs)

        try:
            group_message_field = cls.__annotations__["group_message"]
        except (KeyError, AttributeError) as e:
            raise TypeError(
                f"Class {cls.__name__!r} must define a 'group_message' field"
            ) from e

        # Check if it's a Union type
        origin = get_origin(group_message_field)
        if origin is Union or origin is UnionType:
            # Get all union members
            args = get_args(group_message_field)

            # Validate all union members are BaseGroupMessage subclasses
            for arg in args:
                if not issubclass(arg, BaseGroupMessage):
                    raise TypeError(
                        f"All union members in 'group_message' field of {cls.__name__!r} must be "
                        f"subclasses of BaseGroupMessage, got {arg}"
                    )
        # Or a direct BaseGroupMessage subclass
        elif not (
            group_message_field is BaseGroupMessage
            or (
                isinstance(group_message_field, type)
                and issubclass(group_message_field, BaseGroupMessage)
            )
        ):
            raise TypeError(
                f"The 'group_message' field of {cls.__name__!r} must be BaseGroupMessage "
                f"or a union of BaseGroupMessage subclasses, got {group_message_field}"
            )

        has_discriminator_group_message_field = False
        if hasattr(cls, "group_message") and cls.group_message.discriminator is not None:  # type: ignore
            has_discriminator_group_message_field = True

        # Add discriminator automatically if not explicitly set
        if not has_discriminator_group_message_field:
            # Check if there's a settings module with MESSAGE_ACTION_KEY
            from chanx.settings import chanx_settings

            # Update the field with discriminator
            cls.model_fields["group_message"] = Field(
                discriminator=chanx_settings.MESSAGE_ACTION_KEY
            )
