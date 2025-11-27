"""reliable_chat client."""

from ..base.client import BaseClient
from .messages import IncomingMessage, OutgoingMessage


class ReliableChatClient(BaseClient):
    """
    WebSocket client for reliable_chat.

    Reliable Chat Consumer using queue-based layer

    Channel: /ws/reliable
    """

    path = "/ws/reliable"
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
