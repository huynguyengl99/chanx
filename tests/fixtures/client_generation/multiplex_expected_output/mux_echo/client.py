"""mux_echo multiplexed sub-client."""

from ..base.demultiplexer import BaseSubClient
from .messages import IncomingMessage, OutgoingMessage


class MuxEchoClient(BaseSubClient):
    """
    WebSocket sub-client for mux_echo.

    Echo consumer, reached through the demultiplexer

    Reached under the envelope key "echo" on /ws/mux;
    it has no connection of its own. Register it on the demultiplexer client and
    override handle_message as usual.
    """

    consumer_key = "echo"
    incoming_message = IncomingMessage

    async def send_message(self, message: OutgoingMessage) -> None:
        """
        Send a message to this consumer.

        Args:
            message: The message to send
        """
        await super().send_message(message)

    async def handle_message(self, message: IncomingMessage) -> None:
        pass
