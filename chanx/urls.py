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
def path(
    route: _StrOrPromise, view: Any, kwargs: Any = None, name: str | None = None
) -> Any:
    return base_path(  # pyright: ignore[reportUnknownVariableType, reportCallIssue]
        route, view, kwargs, name  # pyright: ignore[reportArgumentType]
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
def re_path(
    route: _StrOrPromise, view: Any, kwargs: Any = None, name: str | None = None
) -> Any:
    return base_re_path(  # pyright: ignore[reportUnknownVariableType, reportCallIssue]
        route, view, kwargs, name  # pyright: ignore[reportArgumentType]
    )
