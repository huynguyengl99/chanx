"""One connection serving several topics, plus the same topic on its own route."""

from typing import Any, ClassVar

from chanx.core.decorators import channel, ws_handler
from chanx.core.topic import Topic
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.base_consumer import BaseConsumer

from .messages import (
    EchoMessage,
    PostedMessage,
    PostMessage,
    PresenceChanged,
    RoomEvent,
)


class RoomTopic(Topic[RoomEvent]):
    """A chat room, addressed as room:<room_name>."""

    pattern = "room:{room_name}"
    channel_layer_alias = "chat"

    @ws_handler(summary="Post to a room")
    async def handle_post(self, message: PostMessage) -> None:
        await RoomTopic.broadcast(self.topic, RoomEvent(payload=message.payload))

    @ws_handler(summary="Acknowledge without broadcasting")
    async def handle_echo(self, message: EchoMessage) -> PostedMessage:
        return PostedMessage(payload=message.payload)

    passthrough_events: ClassVar[list[Any]] = [RoomEvent]


class PresenceTopic(Topic[PresenceChanged]):
    """Presence for one user, addressed as presence:<user>."""

    pattern = "presence:{user}"
    channel_layer_alias = "chat"

    passthrough_events: ClassVar[list[Any]] = [PresenceChanged]


@channel(
    name="topic_hub",
    description="Several topics multiplexed over a single connection",
    tags=["topics"],
)
class TopicHubConsumer(BaseConsumer[RoomEvent]):
    """Hub serving room and presence topics on one socket."""

    channel_layer_alias = "chat"
    topics: ClassVar[list[type[Topic[Any]]]] = [RoomTopic, PresenceTopic]

    @ws_handler(summary="Handle ping requests")
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()


# The same RoomTopic class, reachable on a dedicated route where connecting is
# the subscription and clients send no envelope.
RoomTopicConsumer = RoomTopic.as_consumer()
