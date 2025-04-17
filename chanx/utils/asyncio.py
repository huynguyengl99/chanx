import asyncio
from collections.abc import Coroutine
from contextvars import Context
from typing import Any, TypeVar

from django.db import close_old_connections

from chanx.utils.logging import logger

global_background_tasks: set[asyncio.Task[Any]] = set()
T = TypeVar("T")


async def wrap_task(coro: Coroutine[Any, Any, T]) -> T:
    """
    Wraps a coroutine with error handling and database connection cleanup.

    This function ensures that any exceptions in the wrapped coroutine are
    properly logged and that database connections are closed after execution,
    preventing connection leaks.

    Args:
        coro: The coroutine to wrap

    Returns:
        The result from the wrapped coroutine

    Raises:
        Exception: Re-raises any exception from the wrapped coroutine
    """
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
    """
    Creates an asyncio task with proper cleanup and tracking.

    This function creates a task from a coroutine, wrapping it with error handling
    and adding it to a set of background tasks for tracking. The task automatically
    removes itself from the tracking set when completed.

    Args:
        coro: The coroutine to convert into a task
        background_tasks: Set to track the task (uses global set if None)
        name: Optional name for the task
        context: Optional context for the task

    Returns:
        The created asyncio task
    """
    task: asyncio.Task[T] = asyncio.create_task(
        wrap_task(coro), name=name, context=context
    )
    if background_tasks is None:
        background_tasks = global_background_tasks

    background_tasks.add(task)
    task.add_done_callback(lambda _: background_tasks.discard(task))

    return task
