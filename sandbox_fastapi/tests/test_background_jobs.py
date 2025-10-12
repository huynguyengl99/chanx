from typing import Any, cast

import pytest
from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.fast_channels.testing import WebsocketCommunicator
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.apps.background_jobs.consumer import BackgroundJobConsumer
from sandbox_fastapi.apps.background_jobs.messages import (
    JobMessage,
    JobPayload,
    JobStatusMessage,
)
from sandbox_fastapi.main import app


@pytest.mark.asyncio
async def test_connection_established_and_ping_handler() -> None:
    """Test ping-pong functionality."""
    async with WebsocketCommunicator(
        app, "/ws/background_jobs", consumer=BackgroundJobConsumer
    ) as comm:
        connection_messages = await comm.receive_all_messages(stop_action="job_status")
        assert len(connection_messages) == 1
        connection_message = cast(JobStatusMessage, connection_messages[0])
        assert (
            connection_message.payload["message"]
            == "🔄 Background Job Processor: Connected!"
        )

        await comm.send_message(PingMessage())
        replies = await comm.receive_all_messages()

        assert len(replies) == 1
        assert replies == [PongMessage()]


@pytest.mark.asyncio
async def test_job_success(bg_worker: Any) -> None:
    """Test successful job queuing."""
    async with WebsocketCommunicator(
        app, "/ws/background_jobs", consumer=BackgroundJobConsumer
    ) as comm:
        # Skip connection message
        await comm.receive_all_messages(stop_action="job_status")

        # Send job message
        message_to_translate = "hello"
        job_message = JobMessage(
            payload=JobPayload(type="translate", content=message_to_translate)
        )
        await comm.send_message(job_message)

        # Receive queuing and queued messages
        replies = await comm.receive_all_messages()
        assert len(replies) == 2

        # Check queuing message
        queuing_msg = cast(JobStatusMessage, replies[0])
        assert queuing_msg.payload["status"] == "queuing"
        assert "Queuing translate job" in queuing_msg.payload["message"]

        # Check queued message
        queued_msg = cast(JobStatusMessage, replies[1])
        assert queued_msg.payload["status"] == "queued"
        assert "queued successfully" in queued_msg.payload["message"]

        # Process jobs with real ARQ worker
        await bg_worker.async_run()

        results = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)
        assert len(results) == 1
        translated_result = cast(JobStatusMessage, results[0])

        translated_text = f"🌍 Translated: '{message_to_translate}' → 'hola'"
        assert translated_result == JobStatusMessage(
            payload={"status": "result", "message": translated_text}
        )


async def send_job_and_process(job_type: str, content: str, bg_worker: Any) -> str:
    """Helper to send job and process with worker."""
    async with WebsocketCommunicator(
        app, "/ws/background_jobs", consumer=BackgroundJobConsumer
    ) as comm:
        await comm.receive_all_messages(stop_action="job_status")  # Skip connection

        await comm.send_message(
            JobMessage(payload=JobPayload(type=job_type, content=content))
        )
        await comm.receive_all_messages()  # Skip queuing messages
        await bg_worker.async_run()

        results = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)
        result = cast(JobStatusMessage, results[0])
        return cast(str, result.payload["message"])


@pytest.mark.asyncio
async def test_analyze_job(bg_worker: Any) -> None:
    """Test analyze job type."""
    result = await send_job_and_process("analyze", "hello world test", bg_worker)
    assert "📊 Analysis of" in result and "Words: 3" in result


@pytest.mark.asyncio
async def test_generate_weather_job(bg_worker: Any) -> None:
    """Test generate job with weather query."""
    result = await send_job_and_process("generate", "weather today", bg_worker)
    assert "🤖 AI Response" in result and "weather" in result.lower()


@pytest.mark.asyncio
async def test_generate_food_job(bg_worker: Any) -> None:
    """Test generate job with food query."""
    result = await send_job_and_process("generate", "what to eat", bg_worker)
    assert "🤖 AI Response" in result and (
        "restaurant" in result.lower() or "pasta" in result.lower()
    )


@pytest.mark.asyncio
async def test_generate_help_job(bg_worker: Any) -> None:
    """Test generate job with help query."""
    result = await send_job_and_process("generate", "need help", bg_worker)
    assert "🤖 AI Response" in result and "help" in result.lower()


@pytest.mark.asyncio
async def test_default_job(bg_worker: Any) -> None:
    """Test default job type."""
    result = await send_job_and_process("default", "test content", bg_worker)
    assert result == "✅ Processed: TEST CONTENT"


@pytest.mark.asyncio
async def test_invalid_job_type(bg_worker: Any) -> None:
    """Test invalid job type defaults to default."""
    result = await send_job_and_process("invalid_type", "test content", bg_worker)
    assert result == "✅ Processed: TEST CONTENT"


@pytest.mark.asyncio
async def test_job_queuing_error() -> None:
    """Test job queuing error handling."""
    async with WebsocketCommunicator(
        app, "/ws/background_jobs", consumer=BackgroundJobConsumer
    ) as comm:
        # Skip connection message
        await comm.receive_all_messages(stop_action="job_status")

        # Mock the queue_job function to raise an exception
        from unittest.mock import patch

        with patch(
            "sandbox_fastapi.apps.background_jobs.consumer.queue_job"
        ) as mock_queue:
            mock_queue.side_effect = Exception("Redis connection failed")

            # Send job message
            job_message = JobMessage(
                payload=JobPayload(type="translate", content="hello")
            )
            await comm.send_message(job_message)

            # Should receive queuing message and then error message
            replies = await comm.receive_all_messages()
            assert len(replies) == 2

            # Check queuing message
            queuing_msg = cast(JobStatusMessage, replies[0])
            assert queuing_msg.payload["status"] == "queuing"

            # Check error message
            error_msg = cast(JobStatusMessage, replies[1])
            assert error_msg.payload["status"] == "error"
            assert "Error queuing job" in error_msg.payload["message"]
            assert "Redis connection failed" in error_msg.payload["message"]


@pytest.mark.asyncio
async def test_translations(bg_worker: Any) -> None:
    """Test translation variations."""
    test_cases = [
        ("hello", "hola"),
        ("world", "mundo"),
        ("unknown phrase", "[TRANSLATED: unknown phrase]"),
    ]

    for input_text, expected_translation in test_cases:
        result = await send_job_and_process("translate", input_text, bg_worker)
        expected = f"🌍 Translated: '{input_text}' → '{expected_translation}'"
        assert result == expected
