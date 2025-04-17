from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.generics import ChanxAuthView
from chanx.messages.base import BaseMessage

from chat.messages.chat_message import ChatIncomingMessage
from chat.models import GroupChat
from chat.permissions import IsGroupChatMember


class ChatAuthAPIView(ChanxAuthView):
    permission_classes = [IsGroupChatMember]
    queryset = GroupChat.objects.get_queryset()


class ChatDetailConsumer(AsyncJsonWebsocketConsumer):
    auth_method = "get"
    auth_class = ChatAuthAPIView
    INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        pass
