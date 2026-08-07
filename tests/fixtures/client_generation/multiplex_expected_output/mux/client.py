"""mux demultiplexer client."""

from ..base.demultiplexer import BaseDemultiplexerClient
from ..mux_chat import MuxChatClient
from ..mux_echo import MuxEchoClient
from .messages import IncomingMessage, OutgoingMessage


class MuxClient(BaseDemultiplexerClient):
    """
    WebSocket client for mux, serving several consumers at once.

    Demultiplexer serving the echo and chat consumers

    Channel: /ws/mux

    Each consumer is a sub-client on this instance, reached through
    ``self.consumers["<key>"]``:
    - "echo" -> MuxEchoClient
    - "chat" -> MuxChatClient

    Override on_ready() to learn which consumers are addressable and to replay
    per-key subscriptions, and on_stream_unavailable() to react to one going away.
    """

    path = "/ws/mux"
    incoming_message = IncomingMessage

    consumer_field = "consumer"
    message_field = "message"
    version_field = "version"
    envelope_version = 1

    sub_client_classes = {
        "echo": MuxEchoClient,
        "chat": MuxChatClient,
    }

    async def send_message(
        self, message: OutgoingMessage, *, consumer: str | None = None
    ) -> None:
        """
        Send a message to one consumer, or to the demultiplexer itself.

        Args:
            message: The message to send
            consumer: Envelope key to address; omit for the demultiplexer's own
                      handlers
        """
        await super().send_message(message, consumer=consumer)

    async def handle_message(self, message: IncomingMessage) -> None:
        """Handle a message the demultiplexer sent on its own behalf."""
        pass
