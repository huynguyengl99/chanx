import asyncio
from collections.abc import Coroutine
from contextvars import Context
from typing import Any, TypeVar

from django.db import close_old_connections

from chanx.utils.logging import logger

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
