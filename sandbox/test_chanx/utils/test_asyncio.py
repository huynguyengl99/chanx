from contextvars import Context
from unittest.mock import AsyncMock, patch

from django.test import TestCase

from chanx.utils.asyncio import create_task, global_background_tasks, wrap_task


class TestAsyncUtils(TestCase):
    """Test cases for custom asyncio utility functions."""

    def setUp(self):
        # Clear global background tasks before each test
        global_background_tasks.clear()

    def tearDown(self):
        # Clear global background tasks after each test
        global_background_tasks.clear()

    async def test_wrap_task_exception_handling(self):
        """Test exception handling in wrap_task."""

        # Create a coroutine that will raise an exception
        async def failing_coro():
            raise ValueError("Test exception")

        # Mock the logger to verify it's called
        with patch(
            "chanx.utils.asyncio.logger.aexception", new_callable=AsyncMock
        ) as mock_logger:
            # The exception should be re-raised
            with self.assertRaises(ValueError):
                await wrap_task(failing_coro())

            # Verify logger was called with expected arguments
            mock_logger.assert_awaited_once()
            args, kwargs = mock_logger.await_args
            assert args[0] == "Test exception"
            assert kwargs["reason"] == "Async task has error."

    async def test_create_task_with_global_background_tasks(self):
        """Test create_task using global background tasks."""

        # Create a simple coroutine
        async def sample_coro():
            return "result"

        # Call create_task without specifying background_tasks
        task = create_task(sample_coro())

        # Verify the task was added to global_background_tasks
        assert task in global_background_tasks

        # Wait for the task to complete
        result = await task

        # Verify the task was removed from global_background_tasks
        assert task not in global_background_tasks
        assert result == "result"

    async def test_create_task_with_custom_background_tasks(self):
        """Test create_task using custom background tasks set."""
        # Create a custom background tasks set
        custom_background_tasks = set()

        # Create a simple coroutine
        async def sample_coro():
            return "result"

        # Call create_task with custom background_tasks
        task = create_task(sample_coro(), background_tasks=custom_background_tasks)

        # Verify the task was added to custom_background_tasks
        assert task in custom_background_tasks
        assert task not in global_background_tasks

        # Wait for the task to complete
        result = await task

        # Verify the task was removed from custom_background_tasks
        assert task not in custom_background_tasks
        assert result == "result"

    async def test_create_task_with_name_and_context(self):
        """Test create_task with name and context parameters."""

        # Create a simple coroutine
        async def sample_coro():
            return "result"

        # Create a new context
        ctx = Context()

        # Call create_task with name and context
        task = create_task(sample_coro(), name="test_task", context=ctx)

        # Verify the task name
        assert task.get_name() == "test_task"

        # Wait for the task to complete and verify the result
        result = await task
        assert result == "result"
