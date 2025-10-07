from channels.layers import get_channel_layer

from accounts.models import User

from chat.consumers.chat_detail import ChatDetailConsumer
from chat.consumers.group import GroupChatConsumer
from chat.messages.chat import (
    MemberRemovedPayload,
    NotifyMemberAddedEvent,
    NotifyMemberRemovedEvent,
)
from chat.messages.group import (
    GroupRemovePayload,
    NotifyAddedToGroupEvent,
    NotifyRemovedFromGroupEvent,
)
from chat.models import ChatMember, GroupChat
from chat.serializers import GroupChatSerializer, ManageChatMemberSerializer
from chat.utils import make_user_groups_layer_name, name_group_chat

channel_layer = get_channel_layer()


def task_handle_new_group_member(user_id: int, group_chat_id: int) -> None:
    """
    Notify a user when they are added to a group chat.

    Args:
        user_id: The user ID of the new member
        group_chat_id: The group chat ID
    """
    # Get the group chat data for the notification
    group_chat = GroupChat.objects.get(id=group_chat_id)
    group_serializer = GroupChatSerializer(group_chat)

    # Find the member
    member = ChatMember.objects.get(user_id=user_id, group_chat_id=group_chat_id)
    member_serializer = ManageChatMemberSerializer(member)

    assert channel_layer is not None

    # 1. Notify the added user through their personal channel
    user_group = make_user_groups_layer_name(user_id)
    GroupChatConsumer.broadcast_event_sync(
        NotifyAddedToGroupEvent(
            payload=group_serializer.data,  # pyright: ignore[reportUnknownArgumentType]
        ),
        [user_group],
    )

    # 2. Notify the chat detail page (for users already viewing that page)
    chat_group = name_group_chat(group_chat_id)

    ChatDetailConsumer.broadcast_event_sync(
        NotifyMemberAddedEvent(
            payload=member_serializer.data  # pyright: ignore[reportUnknownArgumentType]
        ),
        [chat_group],
    )


def task_handle_remove_group_member(user_id: int, group_chat_id: int) -> None:
    """
    Notify a user when they are removed from a group chat.

    Args:
        user_id: The user ID of the removed member
        group_chat_id: The group chat ID
    """
    assert channel_layer is not None

    # Try to get the group chat and user info
    group_chat = GroupChat.objects.get(id=group_chat_id)
    user = User.objects.get(id=user_id)

    # 1. Notify the removed user through their personal channel
    user_group = make_user_groups_layer_name(user_id)
    GroupChatConsumer.broadcast_event_sync(
        NotifyRemovedFromGroupEvent(
            payload=GroupRemovePayload(
                group_pk=group_chat.pk, group_title=group_chat.title
            ),
        ),
        [user_group],
    )

    # 2. Also notify the chat detail page (for other users viewing that page)
    chat_group = name_group_chat(group_chat_id)
    ChatDetailConsumer.broadcast_event_sync(
        NotifyMemberRemovedEvent(
            payload=MemberRemovedPayload(
                user_pk=user_id,
                email=user.email,
            )
        ),
        [chat_group],
    )
