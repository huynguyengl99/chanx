"""background_jobs client."""

from ..base.client import BaseClient
from .messages import IncomingMessage, OutgoingMessage


class BackgroundJobsClient(BaseClient):
    """
    WebSocket client for background_jobs.

    Background Jobs Consumer - Real background job processing with ARQ

    Channel: /ws/background_jobs
    """

    path = "/ws/background_jobs"
    incoming_message = IncomingMessage

    async def send_message(self, message: OutgoingMessage) -> None:
        """
        Send a message to the server.

        Args:
            message: The message to send (Pydantic model or dict)
        """
        await super().send_message(message)

    async def handle_message(self, message: IncomingMessage) -> None:
        pass
