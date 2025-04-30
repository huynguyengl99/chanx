from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from discussion.messages.discussion import (
    DiscussionGroupMessage,
    DiscussionIncomingMessage,
    DiscussionMemberMessage,
    DiscussionMessagePayload,
    NewDiscussionMessage,
)


class DiscussionConsumer(AsyncJsonWebsocketConsumer):
    """Websocket to chat in discussion, with anonymous users."""

    INCOMING_MESSAGE_SCHEMA = DiscussionIncomingMessage
    OUTGOING_GROUP_MESSAGE_SCHEMA = DiscussionGroupMessage
    permission_classes = []

    groups = ["discussion"]

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                # Reply with a PONG message
                await self.send_message(PongMessage())
            case NewDiscussionMessage(payload=discussion_payload):

                if discussion_payload.raw:
                    await self.send_to_groups({"message": discussion_payload.content})
                else:
                    # Echo back with a reply message
                    await self.send_group_message(
                        DiscussionMemberMessage(
                            payload=DiscussionMessagePayload(
                                content=discussion_payload.content,
                            )
                        ),
                    )
