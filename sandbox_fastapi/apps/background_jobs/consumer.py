"""
Background Jobs Consumer - Real background job processing with ARQ.
Migrated to use chanx framework.
"""

from chanx.core.decorators import channel, event_handler, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.base_consumer import BaseConsumer
from sandbox_fastapi.tasks import queue_job

from .messages import JobMessage, JobResult, JobStatusMessage


@channel(
    name="background_jobs",
    description="Background Jobs Consumer - Real background job processing with ARQ",
    tags=["jobs", "background", "arq"],
)
class BackgroundJobConsumer(BaseConsumer[JobResult]):
    """
    Consumer for processing messages with real background jobs using ARQ.
    Migrated to use chanx framework.
    """

    channel_layer_alias = "chat"

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle job processing requests",
        description="Process job requests by queuing them with ARQ",
        output_type=JobStatusMessage,
    )
    async def handle_job(self, message: JobMessage) -> None:
        """Handle incoming job messages."""
        try:
            job_type = message.payload.type
            content = message.payload.content

            # Show immediate response that job is being queued
            await self.send_message(
                JobStatusMessage(
                    payload={
                        "status": "queuing",
                        "message": f"⏳ Queuing {job_type} job: {content}",
                    }
                )
            )

            # Queue the real background job (now async)
            job_id = await queue_job(job_type, content, self.channel_name)

            await self.send_message(
                JobStatusMessage(
                    payload={
                        "status": "queued",
                        "job_id": job_id,
                        "message": (
                            f"📋 Job {job_id} queued successfully! Worker will process it shortly..."
                        ),
                    }
                )
            )

        except Exception as e:
            await self.send_message(
                JobStatusMessage(
                    payload={
                        "status": "error",
                        "message": f"❌ Error queuing job: {str(e)}",
                    }
                )
            )

    async def post_authentication(self) -> None:
        """Send connection established message."""
        await self.send_message(
            JobStatusMessage(
                payload={
                    "status": "connected",
                    "message": "🔄 Background Job Processor: Connected!",
                }
            )
        )

    @event_handler
    async def handle_job_result(self, event: JobResult) -> JobStatusMessage:
        """
        Handle job results sent back from background workers.
        """
        return JobStatusMessage(payload={"status": "result", "message": event.payload})
