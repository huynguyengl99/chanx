"""chat client."""

from ..base.client import BaseClient
from .messages import IncomingMessage, OutgoingMessage


class ChatClient(BaseClient):
    """
    WebSocket client for chat.

    Basic Chat Consumer using centralized chat layer

    Channel: /ws/chat
    """

    path = "/ws/chat"
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
