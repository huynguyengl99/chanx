from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage


class ChatConsumer(AsyncJsonWebsocketConsumer):

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        pass
