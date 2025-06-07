import uuid
from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from assistants.messages.assistant import (
    AssistantIncomingMessage,
    MessagePayload,
    NewMessage,
    ReplyMessage,
    StreamingMessage,
    StreamingReplyCompleteMessage,
    StreamingReplyMessage,
)
from assistants.utils import tokenize_for_streaming


class AssistantConsumer(AsyncJsonWebsocketConsumer[AssistantIncomingMessage]):
    """Websocket to chat with server, like chat with chatbot system"""

    permission_classes = []
    authentication_classes = []

    async def receive_message(
        self, message: AssistantIncomingMessage, **kwargs: Any
    ) -> None:
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
            case StreamingMessage():
                await self._handle_streaming_message(message)

    async def _handle_streaming_message(self, message: StreamingMessage) -> None:
        content = message.payload.content
        tokens = tokenize_for_streaming(content)
        msg_id = str(uuid.uuid4())
        for token in tokens:
            await self.send_message(
                StreamingReplyMessage(
                    payload=StreamingReplyMessage.Payload(content=token, id=msg_id)
                )
            )

        await self.send_message(
            StreamingReplyCompleteMessage(
                payload=StreamingReplyCompleteMessage.Payload(id=msg_id)
            )
        )
