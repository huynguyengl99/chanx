from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import ErrorMessage, PongMessage

from chat.messages.chat import (
    ChatIncomingMessage,
    MessagePayload,
    NewMessage,
    ReplyMessage,
)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Websocket to chat with server, like chat with chatbot system"""

    permission_classes = []
    INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                # Reply with a PONG message
                await self.send_message(PongMessage())
            case NewMessage(payload=payload):
                # Extract the user's message directly from the matched payload
                payload: MessagePayload

                # Echo back with a reply message
                await self.send_message(
                    ReplyMessage(
                        payload=MessagePayload(content=f"Reply: {payload.content}")
                    )
                )

            case _:
                await self.send_message(
                    ErrorMessage(
                        payload={
                            "message": f"Unrecognized message type: {message.action}"
                        }
                    )
                )
