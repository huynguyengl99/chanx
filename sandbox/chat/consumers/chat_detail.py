from typing import Any, cast

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


class ChatDetailConsumer(AsyncJsonWebsocketConsumer[GroupChat]):
    INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage
    OUTGOING_GROUP_MESSAGE_SCHEMA = OutgoingGroupMessage
    permission_classes = [IsGroupChatMember]
    queryset = GroupChat.objects.get_queryset()

    member: ChatMember
    groups: list[str]

    async def build_groups(self) -> list[str]:
        assert self.obj
        self.group_name = name_group_chat(self.obj.pk)
        return [self.group_name]

    async def post_authentication(self) -> None:
        assert self.user is not None
        assert self.obj
        self.member = await self.obj.members.select_related("user").aget(user=self.user)

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())
            case NewChatMessage(payload=message_payload):
                assert self.obj
                new_message = await ChatMessage.objects.acreate(
                    content=message_payload.content,
                    group_chat_id=self.obj.pk,
                    sender=self.member,
                )
                groups = message_payload.groups

                message_serializer = ChatMessageSerializer(instance=new_message)

                await self.send_group_message(
                    MemberMessage(payload=cast(Any, message_serializer.data)),
                    groups=groups,
                    exclude_current=False,
                )
            case JoinGroupMessage(payload=join_group_payload):
                await self.channel_layer.group_add(
                    join_group_payload.group_name, self.channel_name
                )
                self.groups.extend(join_group_payload.group_name)
            case _:
                pass
