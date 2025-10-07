"""
Layers Combo Consumers - Different channel layer types working together.
Migrated to use chanx framework for unified API.
"""

from chanx.core.adapter import WebSocketDisconnectEvent
from chanx.core.decorators import channel, event_handler, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.base_consumer import BaseConsumer

from .messages import (
    AnalyticsMessage,
    AnalyticsNotificationMessage,
    AnalyticsPayload,
    ChatMessage,
    ChatNotificationMessage,
    ChatPayload,
    NotificationBroadcastMessage,
    NotificationMessage,
    NotificationPayload,
    ReliableChatMessage,
    ReliableChatNotificationMessage,
    ReliableChatPayload,
    SystemNotify,
    SystemPeriodicNotify,
)


@channel(
    name="chat",
    description="Basic Chat Consumer using centralized chat layer",
    tags=["chat", "showcase"],
)
class ChatConsumer(BaseConsumer[SystemNotify]):
    """
    Chat consumer using the centralized chat layer.
    Migrated to use chanx framework.
    """

    groups = ["chat_room"]
    channel_layer_alias = "chat"

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle chat messages",
        description="Process chat messages and broadcast to room",
        output_type=ChatNotificationMessage,
    )
    async def handle_chat(self, message: ChatMessage) -> None:
        """Handle incoming chat messages and broadcast to room."""
        await self.broadcast_message(
            ChatNotificationMessage(
                payload=ChatPayload(message=f"💬 {message.payload.message}"),
            ),
        )

    async def post_authentication(self) -> None:
        """Send join message when user connects."""
        await self.broadcast_message(
            ChatNotificationMessage(
                payload=ChatPayload(message="📢 Someone joined the chat")
            ),
        )

    async def websocket_disconnect(self, message: WebSocketDisconnectEvent) -> None:
        """Send leave message when user disconnects."""
        await self.broadcast_message(
            ChatNotificationMessage(
                payload=ChatPayload(message="❌ Someone left the chat.")
            ),
        )
        await super().websocket_disconnect(message)

    @event_handler
    async def system_notify_chat(self, event: SystemNotify) -> ChatNotificationMessage:
        return ChatNotificationMessage(
            payload=ChatPayload(message=event.payload),
        )


@channel(
    name="reliable_chat",
    description="Reliable Chat Consumer using queue-based layer",
    tags=["chat", "reliable", "showcase"],
)
class ReliableChatConsumer(BaseConsumer[SystemNotify]):
    """
    Chat consumer using the queue-based layer for guaranteed message delivery.
    Migrated to use chanx framework.
    """

    channel_layer_alias = "queue"
    groups = ["reliable_chat"]

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle reliable chat messages",
        description="Process reliable chat messages with guaranteed delivery",
        output_type=ReliableChatNotificationMessage,
    )
    async def handle_reliable_chat(self, message: ReliableChatMessage) -> None:
        """Handle incoming reliable chat messages."""
        await self.broadcast_message(
            ReliableChatNotificationMessage(
                payload=ReliableChatPayload(message=f"📨 {message.payload.message}")
            ),
            groups=["reliable_chat"],
        )

    async def post_authentication(self) -> None:
        """Send connection established message."""
        await self.broadcast_message(
            ReliableChatNotificationMessage(
                payload=ReliableChatPayload(
                    message="🔒 Reliable chat connection established!"
                )
            ),
            groups=["reliable_chat"],
        )

    async def websocket_disconnect(self, message: WebSocketDisconnectEvent) -> None:
        """Send disconnect message."""
        await self.broadcast_message(
            ReliableChatNotificationMessage(
                payload=ReliableChatPayload(message="🚪 Left reliable chat!")
            ),
            groups=["reliable_chat"],
        )
        await super().websocket_disconnect(message)

    @event_handler
    async def system_notify_chat(self, event: SystemNotify) -> ChatNotificationMessage:
        return ChatNotificationMessage(
            payload=ChatPayload(message=event.payload),
        )


@channel(
    name="notifications",
    description="Notification Consumer for real-time notifications",
    tags=["notifications", "showcase"],
)
class NotificationConsumer(BaseConsumer):
    """
    Consumer for real-time notifications using JSON messages.
    Migrated to use chanx framework.
    """

    channel_layer_alias = "notifications"
    groups = ["notifications"]

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle notification messages",
        description="Process notification messages and broadcast to all clients",
        output_type=NotificationBroadcastMessage,
    )
    async def handle_notification(self, message: NotificationMessage) -> None:
        """Handle incoming notifications and broadcast to all clients."""
        await self.broadcast_message(
            NotificationBroadcastMessage(
                payload=NotificationPayload(
                    type="user",
                    message=f"🔔 Notification: {message.payload.message}",
                )
            ),
        )

    async def post_authentication(self) -> None:
        """Send connection established notification."""
        await self.broadcast_message(
            NotificationBroadcastMessage(
                payload=NotificationPayload(
                    type="system", message="🔔 Connected to notifications!"
                )
            ),
        )

    @event_handler
    async def system_notify_notification(
        self, event: SystemNotify
    ) -> NotificationBroadcastMessage:
        return NotificationBroadcastMessage(
            payload=NotificationPayload(type="system", message=event.payload)
        )

    @event_handler
    async def system_notify_periodic_notification(
        self, event: SystemPeriodicNotify
    ) -> NotificationBroadcastMessage:
        return NotificationBroadcastMessage(
            payload=NotificationPayload(type="periodic", message=event.payload)
        )


@channel(
    name="analytics",
    description="Analytics Consumer for reliable event delivery",
    tags=["analytics", "showcase"],
)
class AnalyticsConsumer(BaseConsumer[SystemNotify]):
    """
    Consumer for analytics events with reliable delivery.
    Migrated to use chanx framework.
    """

    channel_layer_alias = "analytics"
    groups = ["analytics"]

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle analytics events",
        description="Process analytics events with reliable delivery",
        output_type=AnalyticsNotificationMessage,
    )
    async def handle_analytics(self, message: AnalyticsMessage) -> None:
        """Handle incoming analytics events."""
        await self.broadcast_message(
            AnalyticsNotificationMessage(
                payload=AnalyticsPayload(
                    event=f"📊 Analytics: {message.payload.event}",
                    data=message.payload.data,
                )
            ),
        )

    @event_handler
    async def system_notify_analytic(
        self, event: SystemNotify
    ) -> AnalyticsNotificationMessage:
        return AnalyticsNotificationMessage(
            payload=AnalyticsPayload(
                event=f"{event.payload}",
            )
        )
