"""
Room Chat Consumer - Dynamic room-based messaging.
Migrated to use chanx framework.
"""

from typing import Any

from chanx.core.decorators import channel, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from fast_channels.type_defs import WebSocketDisconnectEvent
from sandbox_fastapi.base_consumer import BaseConsumer

from .messages import RoomChatMessage, RoomMessagePayload, RoomNotificationMessage


@channel(
    name="room_chat",
    description="Room Chat Consumer - Dynamic room-based messaging",
    tags=["chat", "rooms"],
)
class RoomChatConsumer(BaseConsumer):
    """
    Consumer for room-based chat where users can join specific rooms.
    Migrated to use chanx framework.
    """

    channel_layer_alias = "chat"

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.room_name: str | None = None
        self.room_group_name: str | None = None

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle room chat messages",
        description="Process room chat messages and broadcast to room members",
        output_type=RoomNotificationMessage,
    )
    async def handle_room_chat(self, message: RoomChatMessage) -> None:
        """Handle incoming room chat messages."""
        assert self.room_group_name
        await self.broadcast_message(
            RoomNotificationMessage(
                payload=RoomMessagePayload(
                    message=f"💬 {message.payload.message}",
                    room_name=self.room_name,
                )
            ),
            groups=[self.room_group_name],
        )

    async def post_authentication(self) -> None:
        """Join room and send join notification."""
        # Extract room name from path parameters
        self.room_name = self.scope["path_params"]["room_name"]
        self.room_group_name = f"room_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Add room to groups
        if self.room_group_name not in self.groups:
            self.groups.append(self.room_group_name)

        # Send join notification to the room
        await self.broadcast_message(
            RoomNotificationMessage(
                payload=RoomMessagePayload(
                    message=f"🚪 Someone joined room '{self.room_name}'",
                    room_name=self.room_name,
                )
            ),
            groups=[self.room_group_name],
            exclude_current=True,
        )

    async def websocket_disconnect(self, message: WebSocketDisconnectEvent) -> None:
        """Send leave notification when user disconnects."""
        if self.room_group_name:
            # Send leave notification to the room
            await self.broadcast_message(
                RoomNotificationMessage(
                    payload=RoomMessagePayload(
                        message=f"👋 Someone left room '{self.room_name}'",
                        room_name=self.room_name,
                    )
                ),
                groups=[self.room_group_name],
                exclude_current=True,
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        await super().websocket_disconnect(message)
