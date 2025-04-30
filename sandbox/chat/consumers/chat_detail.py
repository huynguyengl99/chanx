from typing import Any

from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from chat.messages.chat import (
    ChatIncomingMessage,
    JoinGroupMessage,
    NewChatMessage,
)
from chat.messages.group import MemberMessage, OutgoingGroupMessage
from chat.models import ChatMember, ChatMessage, GroupChat
from chat.permissions import IsGroupChatMember
from chat.serializers import ChatMessageSerializer
from chat.utils import name_group_chat


class ChatDetailConsumer(AsyncJsonWebsocketConsumer):
    INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage
    OUTGOING_GROUP_MESSAGE_SCHEMA = OutgoingGroupMessage
    permission_classes = [IsGroupChatMember]
    queryset = GroupChat.objects.get_queryset()

    obj: GroupChat
    member: ChatMember
    groups: list[str]

    async def build_groups(self) -> list[str]:
        self.group_name = name_group_chat(self.obj.pk)
        return [self.group_name]

    async def post_authentication(self) -> None:
        assert self.user is not None
        self.member = await self.obj.members.select_related("user").aget(user=self.user)

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())
            case NewChatMessage(payload=message_payload):
                new_message = await ChatMessage.objects.acreate(
                    content=message_payload.content,
                    group_chat=self.obj,
                    sender=self.member,
                )
                groups = message_payload.groups

                message_data = ChatMessageSerializer(new_message).data

                await self.send_group_message(
                    MemberMessage(payload=message_data),
                    groups=groups,
                    exclude_current=False,
                )
            case JoinGroupMessage(payload=join_group_payload):
                await self.channel_layer.group_add(
                    join_group_payload.group_name, self.channel_name
                )
                self.groups.extend(join_group_payload.group_name)
