from typing import Any

from rest_framework.permissions import IsAdminUser

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from sandbox_app.messages.incoming import (
    NewSpeechMessage,
    NewSpeechPayload,
    SpeechMessage,
    SpeechPingMessage,
)


class SpeechConsumer(AsyncJsonWebsocketConsumer):
    permission_classes = [IsAdminUser]
    INCOMING_MESSAGE_SCHEMA = SpeechMessage

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case SpeechPingMessage():
                # Reply with a PONG message
                await self.send_message(BaseMessage(action="pong", payload=None))

            case NewSpeechMessage(payload=payload):
                payload: NewSpeechPayload
                # Extract the user's message directly from the matched payload
                my_speech = payload.my_speech

                # Echo back with a reply message
                await self.send_message(
                    BaseMessage(
                        action="reply",
                        payload={
                            "speech": f"Reply: {my_speech}",
                            "double": payload.n * 2,
                        },
                    )
                )

            case _:
                # Handle any unrecognized message types
                await self.send_message(
                    BaseMessage(
                        action="error",
                        payload={
                            "message": f"Unrecognized message type: {message.action}"
                        },
                    )
                )
