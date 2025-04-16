import contextlib
import functools
import inspect
from collections.abc import Callable, Iterator
from typing import Any, TypeVar, cast

from chanx.settings import chanx_settings

T = TypeVar("T", bound=Callable[..., Any])


def override_chanx_settings(**settings: Any) -> Callable[[T], T]:
    """
    Decorator for overriding chanx settings for the duration of a test function.
    Works with both sync and async functions.

    Usage:
        @override_chanx_settings(SEND_COMPLETION=True)
        async def test_something_async():
            ...

        @override_chanx_settings(SEND_COMPLETION=True)
        def test_something_sync():
            ...
    """

    def decorator(func: T) -> T:
        if inspect.iscoroutinefunction(func):
            # Handle async functions
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with settings_context(**settings):
                    return await func(*args, **kwargs)

            return cast(T, async_wrapper)
        else:
            # Handle synchronous functions
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with settings_context(**settings):
                    return func(*args, **kwargs)

            return cast(T, sync_wrapper)

    return decorator


@contextlib.contextmanager
def settings_context(**settings: Any) -> Iterator[None]:
    """Context manager for overriding chanx settings temporarily."""
    # Initialize user_settings if it doesn't exist
    if not hasattr(chanx_settings, "user_settings"):
        chanx_settings.user_settings = {}

    # Save original settings
    old_settings = {}
    for key in settings:
        old_settings[key] = chanx_settings.user_settings.get(key)

    # Apply new settings and clear cached properties
    for key, value in settings.items():
        chanx_settings.user_settings[key] = value
        with contextlib.suppress(AttributeError):
            delattr(chanx_settings, key)

    try:
        yield
    finally:
        # Restore original settings
        for key in settings:
            if old_settings[key] is not None:
                chanx_settings.user_settings[key] = old_settings[key]
            else:
                chanx_settings.user_settings.pop(key, None)

            # Clear cached properties again
            with contextlib.suppress(AttributeError):
                delattr(chanx_settings, key)
