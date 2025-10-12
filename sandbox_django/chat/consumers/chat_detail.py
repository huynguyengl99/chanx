from rest_framework.permissions import IsAuthenticated

from chanx.channels.authenticator import DjangoAuthenticator
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from chat.messages.chat import (
    ChatDetailEvent,
    MemberAddedMessage,
    MemberRemovedMessage,
    NewChatMessageEvent,
    NotifyMemberAddedEvent,
    NotifyMemberRemovedEvent,
    UserRemovedFromGroupMessage,
)
from chat.messages.member import MemberMessage
from chat.models import ChatMember, GroupChat
from chat.permissions import IsGroupChatMember
from chat.utils import name_group_chat


class ChatDetailAuthenticator(DjangoAuthenticator):
    permission_classes = [IsAuthenticated, IsGroupChatMember]
    queryset = GroupChat.objects.get_queryset()
    obj: ChatMember


class ChatDetailConsumer(AsyncJsonWebsocketConsumer[ChatDetailEvent]):
    """WebSocket consumer for group chat details."""

    authenticator: ChatDetailAuthenticator
    authenticator_class = ChatDetailAuthenticator

    async def post_authentication(self) -> None:
        """Set up after authentication."""
        chat_member = self.authenticator.obj
        group_name = name_group_chat(chat_member.pk)

        await self.channel_layer.group_add(group_name, self.channel_name)
        self.groups.append(group_name)

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @event_handler
    async def handle_member_added(
        self, event: NotifyMemberAddedEvent
    ) -> MemberAddedMessage:
        return MemberAddedMessage(payload=event.payload)

    @event_handler
    async def handle_member_removed(
        self, event: NotifyMemberRemovedEvent
    ) -> UserRemovedFromGroupMessage | MemberRemovedMessage:
        removed_user_pk = event.payload.user_pk
        user = self.authenticator.user
        if user and str(user.pk) == str(removed_user_pk):
            return UserRemovedFromGroupMessage(
                payload=UserRemovedFromGroupMessage.Payload(
                    redirect="/chat/",
                    message="You have been removed from this group chat",
                )
            )
        return MemberRemovedMessage(payload=event.payload)

    @event_handler
    async def handle_new_chat_message(
        self, event: NewChatMessageEvent
    ) -> MemberMessage:
        assert self.authenticator.user
        message_data = event.payload.message_data
        sender_user_id = message_data["sender"]["user_id"]
        message_data["is_mine"] = self.authenticator.user.pk == sender_user_id
        return MemberMessage(payload=message_data)
