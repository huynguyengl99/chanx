from typing import Any

from rest_framework.permissions import IsAuthenticated

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from discussion.messages.discussion import (
    DiscussionEvent,
    DiscussionIncomingMessage,
    DiscussionMemberMessage,
    DiscussionMessagePayload,
    NewDiscussionMessage,
    NotifyEvent,
)


class DiscussionConsumer(
    AsyncJsonWebsocketConsumer[DiscussionIncomingMessage, DiscussionEvent]
):
    """Websocket to chat in discussion, with anonymous users."""

    permission_classes = [IsAuthenticated]

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

    async def receive_event(self, event: DiscussionEvent) -> None:
        match event:
            case NotifyEvent():
                notify_message = f"ATTENTION: {event.payload.content}"

                await self.send_message(
                    DiscussionMemberMessage(
                        payload=DiscussionMessagePayload(content=notify_message)
                    )
                )
