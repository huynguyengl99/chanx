"""
URL routing utilities for Django Channels applications.

This module provides include, path and re_path functions specifically designed for
Django Channels WebSocket and ASGI application routing. These functions create
URLRouter instances for organizing WebSocket consumers and other ASGI applications.

Functions:
    include: Include router from another module for Channels routing.
             Similar to Django's URL include function, but designed for Channels routing.
             Allows for modular organization of WebSocket routing configurations.

    path: Creates a URLRouter for the given route with simplified syntax.
          Specifically designed for Channels consumers and ASGI applications.

    re_path: Creates a URLRouter for the given route using regular expressions.
             Specifically designed for Channels consumers and ASGI applications.

This module is intended for WebSocket and ASGI routing only. For HTTP routing,
use Django's standard django.urls module.
"""

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypeAlias, overload

from channels.routing import URLRouter
from django.urls import path as base_path
from django.urls import re_path as base_re_path

from asgiref.typing import ASGIApplication

if TYPE_CHECKING:
    from channels.consumer import (
        _ASGIApplicationProtocol,  # pragma: no cover ; TYPE CHECK only
    )
    from django.utils.functional import (
        _StrOrPromise,  # pragma: no cover ; TYPE CHECK only
    )

else:
    _StrOrPromise = _ASGIApplicationProtocol = Any


_URLConf: TypeAlias = URLRouter | str | ModuleType


def include(arg: _URLConf) -> URLRouter:
    """
    Include router from another module for Channels routing.

    Similar to Django's URL include function, but designed for Channels routing.
    This allows for modular organization of WebSocket routing configurations.

    This function can handle:
    - A URLRouter instance (returned as-is)
    - A string path to a module with a 'router' attribute
    - A module object with a 'router' attribute

    The 'router' attribute should be a URLRouter instance.

    Args:
        arg: Either a URLRouter instance, a string path to a module, or the module itself.
             For string paths or modules, they should have a 'router' attribute.

    Returns:
        The URLRouter instance from the module.
    """
    if isinstance(arg, URLRouter):
        router = arg
    else:
        if isinstance(arg, str):
            imported_module = import_module(arg)
        else:
            imported_module = arg
        # Get 'router' from the module
        router = imported_module.router

    return router


@overload
def path(
    route: _StrOrPromise,
    view: _ASGIApplicationProtocol,
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLRouter: ...
@overload
def path(
    route: _StrOrPromise, view: URLRouter, kwargs: dict[str, Any] = ..., name: str = ...
) -> URLRouter: ...
@overload
def path(
    route: _StrOrPromise,
    view: ASGIApplication,
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLRouter: ...
def path(route: _StrOrPromise, view: Any, kwargs: Any = None, name: str = "") -> Any:
    """
    Create a URLRouter for the specified route and ASGI application.

    This function creates URLRouter instances specifically for Channels consumers
    and ASGI applications. It uses a simplified URL routing syntax with path
    converters similar to django.urls.path.

    Parameters:
        route: A string or promise that contains a URL pattern with optional
               path converters (e.g., '<int:id>/' or 'chat/<str:room_name>/')
        view: The ASGI application to be called, which can be one of:
              - A Channels consumer (WebSocketConsumer, AsyncConsumer, etc.)
              - A URLRouter instance (for nested routing)
              - An ASGI application
        kwargs: Additional keyword arguments to pass to the consumer
        name: The name of the URL pattern for reverse URL matching

    Returns:
        URLRouter: A URLRouter instance wrapping the route and view

    Note:
        This function is designed for WebSocket and ASGI routing only.
        For HTTP routing, use django.urls.path instead.
    """
    return base_path(  # pyright: ignore[reportUnknownVariableType]
        route, view, kwargs, name
    )


@overload
def re_path(
    route: _StrOrPromise, view: URLRouter, kwargs: dict[str, Any] = ..., name: str = ...
) -> URLRouter: ...
@overload
def re_path(
    route: _StrOrPromise,
    view: ASGIApplication,
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLRouter: ...
def re_path(route: _StrOrPromise, view: Any, kwargs: Any = None, name: str = "") -> Any:
    r"""
    Create a URLRouter for the specified regex route and ASGI application.

    This function creates URLRouter instances specifically for Channels consumers
    and ASGI applications using regular expressions for more complex URL pattern
    matching.

    Parameters:
        route: A string or promise that contains a regular expression pattern
               (e.g., r'^ws/chat/(?P<room_name>\w+)/$')
        view: The ASGI application to be called, which can be one of:
              - A Channels consumer (WebSocketConsumer, AsyncConsumer, etc.)
              - A URLRouter instance (for nested routing)
              - An ASGI application
        kwargs: Additional keyword arguments to pass to the consumer
        name: The name of the URL pattern for reverse URL matching

    Returns:
        URLRouter: A URLRouter instance wrapping the route and view

    Note:
        This function is designed for WebSocket and ASGI routing only.
        For HTTP routing, use django.urls.re_path instead.
    """
    return base_re_path(  # pyright: ignore[reportUnknownVariableType]
        route, view, kwargs, name
    )
