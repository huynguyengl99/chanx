"""
Decorators for Chanx WebSocket handlers.
"""

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import (
    Literal,
    ParamSpec,
    TypeVar,
    get_type_hints,
    overload,
)

from chanx.core.registry import message_registry
from chanx.messages.base import BaseMessage
from chanx.type_defs import AsyncAPIHandlerInfo, ChannelInfo

_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T")


@overload
def _base_handler(
    *,
    kind: Literal["ws", "event"] = "ws",
    action: str | None = None,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    attribute_name: str,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]: ...


@overload
def _base_handler(
    func: Callable[_P, Awaitable[_R]],
    *,
    kind: Literal["ws", "event"] = "ws",
    action: str | None = None,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    attribute_name: str,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> Callable[_P, Awaitable[_R]]: ...


def _base_handler(  # noqa
    func: Callable[_P, Awaitable[_R]] | None = None,
    *,
    kind: Literal["ws", "event"] = "ws",
    action: str | None = None,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    attribute_name: str,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> (
    Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]
    | Callable[_P, Awaitable[_R]]
):
    """
    Base decorator function for both WebSocket and event handlers.

    Args:
        func: The function to decorate
        action: The action name (if not provided, uses function name)
        input_type: Expected input type for validation
        output_type: Expected output type for documentation
        attribute_name: Name of the attribute to store handler info
        description: AsyncAPI description for the operation
        summary: AsyncAPI summary for the operation
        tags: AsyncAPI tags for the operation
    """

    def decorator(  # noqa C901
        fn: Callable[_P, Awaitable[_R]],
    ) -> Callable[_P, Awaitable[_R]]:
        """
        Inner decorator that processes the handler function and adds metadata.

        Args:
            fn: The handler function to decorate

        Returns:
            The decorated function with handler metadata attached
        """
        # Extract input and output types from function annotations if not provided
        final_input_type = input_type
        final_output_type = output_type
        final_action = action

        # Get type hints from function signature
        type_hints = get_type_hints(fn)
        sig = inspect.signature(fn)

        params = list(sig.parameters.values())
        remain = params[1:] if len(params) > 1 else []

        if not final_input_type:
            if not remain:
                raise ValueError(
                    "Must provide input type either by annotate function or input_type parameter"
                )

            final_input_type = remain[0].annotation

        if not final_output_type:
            # Look for output type in return annotation
            return_annotation = type_hints.get("return")
            if return_annotation and return_annotation is not type(None):
                final_output_type = return_annotation

        if not final_action:
            # Fallback to function name
            final_action = fn.__name__

        # Validate that input_type is a BaseMessage subclass if provided
        if not (
            inspect.isclass(final_input_type)
            and issubclass(final_input_type, BaseMessage)
        ):
            raise TypeError(
                f"Input type {final_input_type} for {fn.__name__} must be a BaseMessage subclass."
            )

        # Store handler information on the function
        consumer_name = fn.__qualname__.split(".")[0]

        assert final_input_type
        handler_info: AsyncAPIHandlerInfo = {
            "action": final_action,
            "message_action": final_input_type.model_fields["action"].default,
            "input_type": final_input_type,
            "output_type": final_output_type,
            "method_name": fn.__name__,
            "description": description,
            "summary": summary,
            "tags": tags,
            "consumer_name": consumer_name,
        }

        if kind == "ws":
            message_registry.add(final_input_type, consumer_name)
        if final_output_type:
            message_registry.add(final_output_type, consumer_name)

        @wraps(fn)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            """Wrapper function that preserves the original handler behavior."""
            return await fn(*args, **kwargs)

        setattr(wrapper, attribute_name, handler_info)
        return wrapper

    # Handle both @decorator and @decorator() usage
    if func is None:
        # Called with arguments: @decorator(action="...")
        return decorator
    else:
        # Called without arguments: @decorator
        return decorator(func)


@overload
def ws_handler(
    *,
    action: str | None = None,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]: ...


@overload
def ws_handler(
    func: Callable[_P, Awaitable[_R]],
    *,
    action: str | None = None,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> Callable[_P, Awaitable[_R]]: ...


def ws_handler(
    func: Callable[_P, Awaitable[_R]] | None = None,
    *,
    action: str | None = None,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> (
    Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]
    | Callable[_P, Awaitable[_R]]
):
    """
    Decorator for WebSocket message handlers.

    This decorator marks methods as WebSocket message handlers and optionally
    specifies input/output types for automatic validation and documentation.

    Args:
        func: The function to decorate (when used without parentheses)
        action: The action name this handler responds to. If not provided,
                will use function name.
        input_type: Expected input message type for validation.
        output_type: Expected output message type for documentation.
        description: AsyncAPI description for the operation.
        summary: AsyncAPI summary for the operation.
        tags: AsyncAPI tags for the operation.
    """
    if func is None:
        return lambda f: _base_handler(
            f,
            kind="ws",
            action=action,
            input_type=input_type,
            output_type=output_type,
            attribute_name="_ws_handler_info",
            description=description,
            summary=summary,
            tags=tags,
        )
    return _base_handler(
        func,
        kind="ws",
        action=action,
        input_type=input_type,
        output_type=output_type,
        attribute_name="_ws_handler_info",
        description=description,
        summary=summary,
        tags=tags,
    )


@overload
def event_handler(
    *,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]: ...


@overload
def event_handler(
    func: Callable[_P, Awaitable[_R]],
    *,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> Callable[_P, Awaitable[_R]]: ...


def event_handler(
    func: Callable[_P, Awaitable[_R]] | None = None,
    *,
    input_type: type[BaseMessage] | None = None,
    output_type: type[BaseMessage] | None = None,
    description: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> (
    Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]
    | Callable[_P, Awaitable[_R]]
):
    """
    Decorator for channel event handlers.

    This decorator marks methods as channel event handlers and uses the method name
    as the handler identifier. Input types should be BaseMessage subclasses.

    Args:
        func: The function to decorate (when used without parentheses)
        input_type: Expected input type (BaseMessage subclass) for validation.
        output_type: Expected output type for documentation.
        description: AsyncAPI description for the operation.
        summary: AsyncAPI summary for the operation.
        tags: AsyncAPI tags for the operation.
    """
    if func is None:
        return lambda f: _base_handler(
            f,
            kind="event",
            action=None,
            input_type=input_type,
            output_type=output_type,
            attribute_name="_event_handler_info",
            description=description,
            summary=summary,
            tags=tags,
        )
    return _base_handler(
        func,
        kind="event",
        action=None,
        input_type=input_type,
        output_type=output_type,
        attribute_name="_event_handler_info",
        description=description,
        summary=summary,
        tags=tags,
    )


def channel(
    *,
    name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Callable[[_T], _T]:
    """
    Decorator for WebSocket consumer classes to add AsyncAPI channel metadata.

    This decorator marks consumer classes with channel-level information for AsyncAPI
    documentation generation. The description will be extracted from the class docstring
    if not provided explicitly.

    Args:
        name: Custom channel name (defaults to auto-generated from class name)
        description: Channel description (overrides docstring)
        tags: List of tags for the channel
    """

    def decorator(cls: _T) -> _T:
        """
        Inner decorator that adds channel metadata to the consumer class.

        Args:
            cls: The consumer class to decorate

        Returns:
            The decorated class with channel metadata attached
        """
        # Store channel information on the class
        channel_info: ChannelInfo = {
            "name": name,
            "description": description,
            "tags": tags,
        }

        setattr(cls, "_channel_info", channel_info)  # noqa
        return cls

    return decorator
