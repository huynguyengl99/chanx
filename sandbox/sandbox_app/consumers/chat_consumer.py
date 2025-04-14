from typing import Any

from rest_framework.permissions import IsAdminUser

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import NewMessage, PingMessage
from chanx.messages.outgoing import ErrorMessage
from sandbox_app.messages.outgoing import PongMessage, ReplyMessage, ReplyPayload


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Websocket to chat"""

    permission_classes = [IsAdminUser]

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                # Reply with a PONG message
                await self.send_message(PongMessage())
            case NewMessage(payload=payload):
                # Extract the user's message directly from the matched payload
                user_message = payload.message

                # Echo back with a reply message
                await self.send_message(
                    BaseMessage(
                        action="reply", payload={"message": f"Reply: {user_message}"}
                    )
                )
                await self.send_message(
                    ReplyMessage(payload=ReplyPayload(message=f"Reply: {user_message}"))
                )

            case _:
                await self.send_message(
                    ErrorMessage(
                        payload={
                            "message": f"Unrecognized message type: {message.action}"
                        }
                    )
                )
