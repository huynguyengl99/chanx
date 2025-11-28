"""system client."""

from ..base.client import BaseClient
from .messages import IncomingMessage, OutgoingMessage


class SystemClient(BaseClient):
    """
    WebSocket client for system.

    System Messages Consumer - Direct WebSocket without channel layers

    Channel: /ws/system
    """

    path = "/ws/system"
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
