"""
Portable access to the ASGI scope.

Django Channels puts URL captures under ``scope["url_route"]["kwargs"]`` while
fast-channels uses Starlette's ``scope["path_params"]``. Anything reading either one
directly is locked to a single framework, so these accessors normalise the difference.
"""

from collections.abc import Mapping, MutableMapping
from typing import Any, cast
from urllib.parse import parse_qs

_MISSING = object()

Scope = MutableMapping[str, Any]


def path_params(scope: Scope) -> Mapping[str, Any]:
    """Return URL path captures, whichever framework populated them."""
    url_route = cast("Mapping[str, Any] | None", scope.get("url_route"))
    if url_route is not None:
        kwargs = cast("Mapping[str, Any] | None", url_route.get("kwargs"))
        if kwargs is not None:
            return kwargs

    params = cast("Mapping[str, Any] | None", scope.get("path_params"))
    return params if params is not None else {}


def path_param(scope: Scope, name: str, default: Any = _MISSING) -> Any:
    """
    Return a single URL path capture.

    Raises ``KeyError`` when the parameter is absent and no default is given: a
    missing capture means the route and the consumer disagree, which is worth
    surfacing rather than silently treating as ``None``.

    Args:
        scope: The ASGI scope
        name: Capture to read
        default: Returned instead of raising when the capture is absent
    """
    params = path_params(scope)
    if name in params:
        return params[name]
    if default is _MISSING:
        raise KeyError(f"No path parameter {name!r} in scope")
    return default


def query_params(scope: Scope) -> dict[str, list[str]]:
    """Parse ``scope["query_string"]`` into a dict of lists."""
    raw = scope.get("query_string") or b""
    if isinstance(raw, str):
        raw = raw.encode()
    return parse_qs(raw.decode("utf-8", errors="replace"))


def scope_user(scope: Scope) -> Any | None:
    """
    Return the authenticated user, or None when the connection is anonymous.

    Works with Channels' ``AuthMiddlewareStack`` and with any dependency that stores
    a user on the scope. Django's ``AnonymousUser`` is normalised to ``None``.
    """
    user = scope.get("user")
    if user is None:
        return None
    if getattr(user, "is_authenticated", True) is False:
        return None
    return user
