"""
System Chat Consumer - Direct WebSocket without channel layers.
Migrated to use chanx framework.
"""

from chanx.core.decorators import channel, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.base_consumer import BaseConsumer

from .messages import MessagePayload, SystemEchoMessage, UserMessage


@channel(
    name="system",
    description="System Messages Consumer - Direct WebSocket without channel layers",
    tags=["system", "direct"],
)
class SystemMessageConsumer(BaseConsumer):
    """
    Consumer for system messages without using channel layers.
    Direct connection without group messaging.
    Migrated to use chanx framework.
    """

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(
        summary="Handle message user send to system",
        description="Echo system messages back directly without using channel layers",
    )
    async def handle_system(self, message: UserMessage) -> SystemEchoMessage:
        """Handle system messages and echo them back directly."""
        return SystemEchoMessage(
            payload=MessagePayload(message=f"🔧 System Echo: {message.payload.message}")
        )

    async def post_authentication(self) -> None:
        """Send connection established message directly to client."""
        await self.send_message(
            SystemEchoMessage(
                payload=MessagePayload(message="🔧 System: Connection established!")
            )
        )
