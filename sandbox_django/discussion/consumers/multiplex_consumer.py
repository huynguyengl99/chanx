"""
Demultiplexer serving several discussion consumers over a single route.

A browser page that needs both the topic list feed and group chat updates would
otherwise open two WebSocket connections. Here it opens one and names the target
consumer in each frame::

    -> {"consumer": "topics", "message": {"action": "ping", "payload": null}}
    <- {"consumer": "topics", "message": {"action": "pong", "payload": null}}

Frames without the ``consumer`` field reach the demultiplexer's own handlers.
"""

from rest_framework.permissions import IsAuthenticated

from chanx.channels.authenticator import DjangoAuthenticator
from chanx.channels.multiplex import AsyncJsonWebsocketDemultiplexer
from chanx.core.decorators import channel, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from chat.consumers.group import GroupChatConsumer
from discussion.consumers.list_consumer import DiscussionListConsumer


class DiscussionMultiplexAuthenticator(DjangoAuthenticator):
    permission_classes = [IsAuthenticated]


@channel(
    name="discussion_multiplex",
    description="Demultiplexer serving the discussion list and group chat consumers",
    tags=["discussion", "multiplex"],
)
class DiscussionMultiplexer(AsyncJsonWebsocketDemultiplexer):
    """
    Serves the discussion list and group chat consumers over one connection.

    Both sub-consumers are reused unchanged from their own routes, keeping their
    groups and channel events. The shared connection is authenticated here, and
    each sub-consumer still runs its own authenticator.
    """

    authenticator_class = DiscussionMultiplexAuthenticator

    consumers = {
        "topics": DiscussionListConsumer,
        "group_chat": GroupChatConsumer,
    }

    @ws_handler(
        summary="Handle ping requests for the shared connection",
        description="Answered by the demultiplexer itself, without an envelope",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()
