"""notifications client."""

from ..base.client import BaseClient
from .messages import IncomingMessage, OutgoingMessage


class NotificationsClient(BaseClient):
    """
    WebSocket client for notifications.

    Notification Consumer for real-time notifications

    Channel: /ws/notifications
    """

    path = "/ws/notifications"
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
