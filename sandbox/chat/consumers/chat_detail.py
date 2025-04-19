from collections.abc import Iterable
from typing import Any, cast

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from chat.messages.chat import ChatIncomingMessage, MessagePayload, NewChatMessage
from chat.messages.group import MemberMessage, OutgoingGroupMessage
from chat.models import ChatMessage, GroupChat
from chat.permissions import IsGroupChatMember
from chat.serializers import ChatMessageSerializer
from chat.utils import name_group_chat


class ChatDetailConsumer(AsyncJsonWebsocketConsumer):
    INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage
    OUTGOING_GROUP_MESSAGE_SCHEMA = OutgoingGroupMessage
    permission_classes = [IsGroupChatMember]
    queryset = GroupChat.objects.get_queryset()

    obj: GroupChat

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(args, kwargs)
        self.member = None

    async def build_groups(self) -> Iterable[str]:
        group = cast(GroupChat, self.obj)
        self.group_name = name_group_chat(group.id)
        return [self.group_name]

    async def post_authentication(self):
        self.member = await self.obj.members.select_related("user").aget(user=self.user)

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())
            case NewChatMessage():
                payload: MessagePayload = message.payload
                new_message = await ChatMessage.objects.acreate(
                    content=payload.content, group_chat=self.obj, sender=self.member
                )

                message = ChatMessageSerializer(new_message).data

                await self.send_group_message(
                    MemberMessage(payload=message), exclude_current=False
                )
