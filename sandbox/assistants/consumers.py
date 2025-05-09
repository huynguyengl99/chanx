from typing import Any

from rest_framework.permissions import IsAuthenticated

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from assistants.messages.assistant import (
    AssistantIncomingMessage,
    MessagePayload,
    NewMessage,
    ReplyMessage,
)


class AssistantConsumer(AsyncJsonWebsocketConsumer):
    """Websocket to chat with server, like chat with chatbot system"""

    INCOMING_MESSAGE_SCHEMA = AssistantIncomingMessage
    permission_classes = [IsAuthenticated]

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                # Reply with a PONG message
                await self.send_message(PongMessage())
            case NewMessage(payload=new_message_payload):

                # Echo back with a reply message
                await self.send_message(
                    ReplyMessage(
                        payload=MessagePayload(
                            content=f"Reply: {new_message_payload.content}"
                        )
                    )
                )
            case _:
                pass
