"""mux_chat multiplexed sub-client."""

from ..base.demultiplexer import BaseSubClient
from .messages import IncomingMessage


class MuxChatClient(BaseSubClient):
    """
    WebSocket sub-client for mux_chat.

    Chat consumer that only broadcasts, reached through the demultiplexer

    Reached under the envelope key "chat" on /ws/mux;
    it has no connection of its own. Register it on the demultiplexer client and
    override handle_message as usual.
    """

    consumer_key = "chat"
    incoming_message = IncomingMessage

    async def handle_message(self, message: IncomingMessage) -> None:
        pass
