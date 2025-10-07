"""
ARQ-based background tasks for the sandbox_fastapi application.
"""

import asyncio
import os
import time
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from sandbox_fastapi.apps.background_jobs.messages import JobResult
from sandbox_fastapi.layers import setup_layers

# Setup channel layers when this module is imported

# ARQ Redis settings - using same Redis instance but different connection approach
redis_url = os.getenv("REDIS_URL", "redis://localhost:6363")
REDIS_SETTINGS = RedisSettings.from_dsn(redis_url)


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize resources when worker starts."""
    # You can set up shared resources here like HTTP clients, database connections, etc.
    setup_layers()


async def shutdown(ctx: dict[str, Any]) -> None:
    """Clean up resources when worker shuts down."""
    # Clean up any shared resources
    pass


async def translate(
    ctx: dict[str, Any], job_id: str, content: str, channel_name: str
) -> dict[str, Any]:
    """
    Simulate text translation task.
    """
    # Simulate async API call delay
    await asyncio.sleep(2)

    # Simple mock translation
    translations = {
        "hello": "hola",
        "world": "mundo",
        "good morning": "buenos días",
        "thank you": "gracias",
    }

    translated = translations.get(content.lower(), f"[TRANSLATED: {content}]")
    result = f"🌍 Translated: '{content}' → '{translated}'"

    # Send result back through channel layer
    await _send_result_to_client(channel_name, result)

    return {"status": "completed", "result": result, "job_id": job_id}


async def analyze(
    ctx: dict[str, Any], job_id: str, content: str, channel_name: str
) -> dict[str, Any]:
    """
    Simulate text analysis task.
    """
    # Simulate async processing delay
    await asyncio.sleep(3)

    # Perform analysis
    word_count = len(content.split())
    char_count = len(content)
    vowel_count = sum(1 for char in content.lower() if char in "aeiou")
    consonant_count = sum(
        1 for char in content.lower() if char.isalpha() and char not in "aeiou"
    )

    result = (
        f"📊 Analysis of '{content}':\n"
        f"• Characters: {char_count}\n"
        f"• Words: {word_count}\n"
        f"• Vowels: {vowel_count}\n"
        f"• Consonants: {consonant_count}"
    )

    # Send result back through channel layer
    await _send_result_to_client(channel_name, result)

    return {"status": "completed", "result": result, "job_id": job_id}


# Keep the old name for backwards compatibility
analyze_text = analyze


async def generate(
    ctx: dict[str, Any], job_id: str, content: str, channel_name: str
) -> dict[str, Any]:
    """
    Simulate AI response generation.
    """
    # Simulate async AI processing
    await asyncio.sleep(4)

    # Simple response generation based on keywords
    if "weather" in content.lower():
        response = "The weather is looking great today! Perfect for a walk outside."
    elif "food" in content.lower() or "eat" in content.lower():
        response = "I'd recommend trying that new restaurant downtown. Their pasta is excellent!"
    elif "help" in content.lower():
        response = "I'm here to help! Feel free to ask me anything you'd like to know."
    else:
        response = f"That's an interesting point about '{content}'. Let me think about that... Based on my analysis, I would suggest exploring this topic further through research and practical application."

    result = f"🤖 AI Response to '{content}':\n{response}"

    # Send result back through channel layer
    await _send_result_to_client(channel_name, result)

    return {"status": "completed", "result": result, "job_id": job_id}


# Keep the old name for backwards compatibility
generate_response = generate


async def default(
    ctx: dict[str, Any], job_id: str, content: str, channel_name: str
) -> dict[str, Any]:
    """
    Default processing task.
    """
    # Quick async processing
    await asyncio.sleep(1)

    result = f"✅ Processed: {content.upper()}"

    # Send result back through channel layer
    await _send_result_to_client(channel_name, result)

    return {"status": "completed", "result": result, "job_id": job_id}


# Keep the old name for backwards compatibility
process_default = default


async def _send_result_to_client(channel_name: str, message: str) -> None:
    """
    Send the result back to the WebSocket client through the channel layer.
    """
    try:
        # Import here to avoid circular imports
        from sandbox_fastapi.apps.background_jobs.consumer import BackgroundJobConsumer

        # Use asgiref to convert async call to sync if needed
        await BackgroundJobConsumer.send_event(JobResult(payload=message), channel_name)

    except Exception as e:
        print(f"Error sending result to client: {e}")


# Job dispatcher mapping
JOB_FUNCTIONS = {
    "translate": translate,
    "analyze": analyze,
    "generate": generate,
    "default": default,
}


async def queue_job(job_type: str, content: str, channel_name: str) -> str:
    """
    Queue a background job and return the job ID.
    """
    if job_type not in JOB_FUNCTIONS:
        job_type = "default"

    # Create ARQ pool connection
    redis = await create_pool(REDIS_SETTINGS)

    try:
        # Generate job ID
        job_id = f"{job_type}_{int(time.time())}"

        # Enqueue the job
        job = await redis.enqueue_job(
            job_type,  # function name as registered in WorkerSettings
            job_id,
            content,
            channel_name,
        )

        return job.job_id if job else job_id

    finally:
        await redis.aclose()


class WorkerSettings:
    """
    ARQ Worker settings.
    """

    functions = [translate, analyze, generate, default]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS_SETTINGS
    # Optional: configure other settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour
