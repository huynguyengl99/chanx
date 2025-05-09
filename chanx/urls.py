"""
URL routing utilities for Django Channels applications.

This module provides path and re_path functions that extend Django's URL routing capabilities
to work with ASGI applications and Django Channels consumers. The functions support both
synchronous Django views and asynchronous ASGI applications.

Functions:
    path: Creates a URL pattern for the given route with simplified syntax.
           Similar to django.urls.path but supports Channels consumers and ASGI applications.

    re_path: Creates a URL pattern for the given route using regular expressions.
             Similar to django.urls.re_path but supports Channels consumers and ASGI applications.

The module ensures proper type checking for different types of views and applications,
supporting URLRouter, ASGIApplication, synchronous and asynchronous HTTP handlers,
and included URL configurations.
"""

from collections.abc import Callable, Coroutine, Sequence
from typing import TYPE_CHECKING, Any, overload

from channels.routing import URLRouter
from django.http import HttpResponseBase
from django.urls import URLPattern, URLResolver
from django.urls import path as base_path
from django.urls import re_path as base_re_path

from asgiref.typing import ASGIApplication

if TYPE_CHECKING:
    from channels.consumer import (
        _ASGIApplicationProtocol,  # pragma: no cover ; TYPE CHECK only
    )
    from django.urls.conf import _IncludedURLConf  # pragma: no cover ; TYPE CHECK only
    from django.utils.functional import (
        _StrOrPromise,  # pragma: no cover ; TYPE CHECK only
    )

else:
    _StrOrPromise = _IncludedURLConf = _ASGIApplicationProtocol = Any


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
@overload
def path(
    route: _StrOrPromise,
    view: Callable[..., HttpResponseBase],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLPattern: ...
@overload
def path(
    route: _StrOrPromise,
    view: Callable[..., Coroutine[Any, Any, HttpResponseBase]],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLPattern: ...
def path(route: _StrOrPromise, view: Any, kwargs: Any = None, name: str = "") -> Any:
    """
    Return a URLRouter or URLPattern for the specified route and view.

    This function extends Django's url routing to support both Django views and
    ASGI applications/Channels consumers. It uses a simplified URL routing syntax
    with path converters similar to django.urls.path.

    Parameters:
        route: A string or promise that contains a URL pattern with optional
               path converters (e.g., '<int:id>/' or 'chat/<str:room_name>/')
        view: The view to be called, which can be one of:
              - An ASGI application (Channels consumer)
              - A URLRouter instance (for nested routing)
              - A Django view function (synchronous or asynchronous)
        kwargs: Additional keyword arguments to pass to the view
        name: The name of the URL pattern for reverse URL matching

    Returns:
        URLRouter: If the view is an ASGI application or a URLRouter
        URLPattern: If the view is a Django view function
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
@overload
def re_path(
    route: _StrOrPromise,
    view: Callable[..., HttpResponseBase],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLPattern: ...
@overload
def re_path(
    route: _StrOrPromise,
    view: Callable[..., Coroutine[Any, Any, HttpResponseBase]],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLPattern: ...
@overload
def re_path(
    route: _StrOrPromise,
    view: _IncludedURLConf,
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLResolver: ...
@overload
def re_path(
    route: _StrOrPromise,
    view: Sequence[URLResolver | str],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLResolver: ...
def re_path(route: _StrOrPromise, view: Any, kwargs: Any = None, name: str = "") -> Any:
    r"""
    Return a URLRouter, URLPattern, or URLResolver for the specified regex route and view.

    This function extends Django's regex-based URL routing to support both Django views
    and ASGI applications/Channels consumers. It uses regular expressions for more
    complex URL pattern matching.

    Parameters:
        route: A string or promise that contains a regular expression pattern
               (e.g., r'^ws/chat/(?P<room_name>\w+)/$')
        view: The view to be called, which can be one of:
              - An ASGI application (Channels consumer)
              - A URLRouter instance (for nested routing)
              - A Django view function (synchronous or asynchronous)
              - An included URL configuration
              - A sequence of URLResolvers or strings
        kwargs: Additional keyword arguments to pass to the view
        name: The name of the URL pattern for reverse URL matching

    Returns:
        URLRouter: If the view is an ASGI application or a URLRouter
        URLPattern: If the view is a Django view function
        URLResolver: If the view is an included URL configuration or sequence
    """
    return base_re_path(  # pyright: ignore[reportUnknownVariableType]
        route, view, kwargs, name
    )
