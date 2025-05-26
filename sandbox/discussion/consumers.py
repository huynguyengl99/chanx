from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from discussion.messages.discussion import (
    DiscussionGroupMessage,
    DiscussionIncomingMessage,
    DiscussionMemberMessage,
    DiscussionMessagePayload,
    NewDiscussionMessage,
)


class DiscussionConsumer(
    AsyncJsonWebsocketConsumer[DiscussionIncomingMessage, DiscussionGroupMessage]
):
    """Websocket to chat in discussion, with anonymous users."""

    permission_classes = []
    authentication_classes = []

    groups = ["discussion"]

    async def receive_message(
        self, message: DiscussionIncomingMessage, **kwargs: Any
    ) -> None:
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
