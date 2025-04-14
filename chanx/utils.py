import asyncio
from collections.abc import Coroutine
from contextvars import Context
from typing import (
    Any,
    TypeVar,
)

from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.http import HttpRequest

import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger("chanx")


global_background_tasks: set[asyncio.Task[Any]] = set()

T = TypeVar("T")


async def wrap_task(coro: Coroutine[Any, Any, T]) -> T:
    try:
        return await coro
    except Exception as e:
        await logger.aexception(str(e), reason="Async task has error.")
        raise  # Re-raising to maintain the original behavior
    finally:
        close_old_connections()


def create_task(
    coro: Coroutine[Any, Any, T],
    background_tasks: set[asyncio.Task[Any]] | None = None,
    name: str | None = None,
    context: Context | None = None,
) -> asyncio.Task[T]:
    task: asyncio.Task[T] = asyncio.create_task(
        wrap_task(coro), name=name, context=context
    )
    if background_tasks is None:
        background_tasks = global_background_tasks

    background_tasks.add(task)
    task.add_done_callback(lambda _: background_tasks.discard(task))

    return task


def request_from_scope(scope: dict[str, Any]) -> HttpRequest:
    request: HttpRequest = HttpRequest()
    request.method = "OPTIONS"
    request.path = scope.get("path", "")
    request.COOKIES = scope.get("cookies", {})
    request.user = scope.get("user", AnonymousUser())

    for header_name, value in scope.get("headers", []):
        trans_header: str = header_name.decode("utf-8").replace("-", "_").upper()
        if not trans_header.startswith("HTTP_"):
            trans_header = "HTTP_" + trans_header
        request.META[trans_header] = value.decode("utf-8")

    return request


def get_request_header(
    request: HttpRequest, header_key: str, meta_key: str
) -> str | None:
    if hasattr(request, "headers"):
        return request.headers.get(header_key)

    return request.META.get(meta_key)
