"""room_chat client."""

from ..base.client import BaseClient
from .messages import IncomingMessage, OutgoingMessage


class RoomChatClient(BaseClient):
    """
    WebSocket client for room_chat.

    Room Chat Consumer - Dynamic room-based messaging

    Channel: /ws/room/{room_name}
    """

    path = "/ws/room/{room_name}"
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
