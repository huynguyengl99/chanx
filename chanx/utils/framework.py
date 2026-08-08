"""
Lazy access to whichever framework integration is in use.

Code written against ``chanx.core`` cannot import a framework at module level without
tying itself to one, so it resolves what it needs through here instead.
"""

from importlib.util import find_spec
from typing import Any, Literal

from chanx.core.check import IS_USING_DJANGO

Framework = Literal["channels", "fast_channels"]


def detect_framework() -> Framework:
    """
    Report which chanx integration is in use.

    Prefers what the environment says, since both can be installed at once, and
    falls back to whichever is importable.
    """
    if IS_USING_DJANGO:
        return "channels"
    if find_spec("fast_channels") is not None:
        return "fast_channels"
    if find_spec("channels") is not None:
        return "channels"
    raise RuntimeError(
        "Neither fast-channels nor channels is installed; install chanx with the "
        '"fast_channels" or "channels" extra.'
    )


def consumer_base() -> Any:
    """Return the concrete consumer base class for the active framework."""
    if detect_framework() == "channels":
        from chanx.channels import websocket as django_websocket

        return django_websocket.AsyncJsonWebsocketConsumer

    from chanx.fast_channels import websocket as fast_websocket

    return fast_websocket.AsyncJsonWebsocketConsumer


def channel_layer(alias: str) -> Any:
    """
    Return a channel layer by alias, from the active framework's registry.

    Args:
        alias: The configured layer alias
    """
    if detect_framework() == "channels":
        from channels.layers import get_channel_layer as django_layer

        return django_layer(alias)

    from fast_channels.layers import get_channel_layer as fast_layer

    return fast_layer(alias)
