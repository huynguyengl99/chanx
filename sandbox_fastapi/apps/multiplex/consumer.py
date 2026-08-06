"""
Multiplex Demultiplexer - Several consumers over a single WebSocket route.

Instead of opening one connection per consumer, the client opens one connection
to ``/ws/mux`` and names the target consumer in each frame::

    -> {"consumer": "system", "message": {"action": "ping", "payload": null}}
    <- {"consumer": "system", "message": {"action": "pong", "payload": null}}

Frames sent without the ``consumer`` field reach the demultiplexer's own handlers,
which is how the shared ping below is reached.
"""

from chanx.core.decorators import channel, ws_handler
from chanx.fast_channels.multiplex import AsyncJsonWebsocketDemultiplexer
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.apps.showcase.consumer import ChatConsumer, NotificationConsumer
from sandbox_fastapi.apps.system_chat.consumer import SystemMessageConsumer


@channel(
    name="multiplex",
    description="Demultiplexer serving the system, chat and notification consumers",
    tags=["multiplex"],
)
class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    """
    Serves several existing consumers over one connection.

    The sub-consumers are reused unchanged from their own routes: each keeps its
    own channel layer, groups and channel events.
    """

    consumers = {
        "system": SystemMessageConsumer,
        "chat": ChatConsumer,
        "notifications": NotificationConsumer,
    }

    @ws_handler(
        summary="Handle ping requests for the shared connection",
        description="Answered by the demultiplexer itself, without an envelope",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()
