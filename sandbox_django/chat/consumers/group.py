from rest_framework.permissions import IsAuthenticated

from asgiref.sync import sync_to_async
from chanx.channels.authenticator import DjangoAuthenticator
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from chat.messages.group import (
    AddedToGroupMessage,
    GroupChatEvent,
    GroupChatUpdatedMessage,
    NotifyAddedToGroupEvent,
    NotifyGroupChatUpdateEvent,
    NotifyRemovedFromGroupEvent,
    RemovedFromGroupMessage,
)
from chat.models import GroupChat
from chat.utils import make_user_groups_layer_name


class GroupChatAuthenticator(DjangoAuthenticator):
    permission_classes = [IsAuthenticated]


class GroupChatConsumer(AsyncJsonWebsocketConsumer[GroupChatEvent]):
    """
    WebSocket consumer for group chat updates.
    """

    authenticator_class = GroupChatAuthenticator
    authenticator: GroupChatAuthenticator

    async def post_authentication(self) -> None:
        assert self.channel_layer
        user = self.authenticator.user
        if not user or not user.is_authenticated:
            return

        assert user.pk
        personal_group = make_user_groups_layer_name(user.pk)
        groups = [personal_group]
        await self.channel_layer.group_add(personal_group, self.channel_name)
        user_group_chats = await sync_to_async(
            lambda: list(
                GroupChat.objects.filter(members__user_id=str(user.pk)).values_list(
                    "pk", flat=True
                )
            )
        )()

        for group_chat_id in user_group_chats:
            group_name = f"group_chat_{group_chat_id}_updates"
            await self.channel_layer.group_add(group_name, self.channel_name)
            groups.append(f"group_chat_{group_chat_id}_updates")

        self.groups.extend(groups)

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @event_handler
    async def handle_notify_added_to_group(
        self, event: NotifyAddedToGroupEvent
    ) -> AddedToGroupMessage:
        group_id = event.payload.get("id")
        await self.channel_layer.group_add(
            f"group_chat_{group_id}_updates", self.channel_name
        )
        return AddedToGroupMessage(payload=event.payload)

    @event_handler
    async def handle_notify_removed_from_group(
        self, event: NotifyRemovedFromGroupEvent
    ) -> RemovedFromGroupMessage:
        group_id = event.payload.group_pk
        await self.channel_layer.group_discard(
            f"group_chat_{group_id}_updates", self.channel_name
        )
        return RemovedFromGroupMessage(payload=event.payload)

    @event_handler
    async def handle_group_chat_update(
        self, event: NotifyGroupChatUpdateEvent
    ) -> GroupChatUpdatedMessage:
        return GroupChatUpdatedMessage(payload=event.payload)
