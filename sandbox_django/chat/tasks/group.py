from channels.layers import get_channel_layer

from chat.consumers.group import GroupChatConsumer
from chat.messages.group import GroupChatUpdatePayload, NotifyGroupChatUpdateEvent
from chat.models import GroupChat

channel_layer = get_channel_layer()


def task_handle_group_chat_update(group_chat_id: int) -> None:
    """
    Handle broadcasting group chat updates to all members of that specific group.

    This function notifies all users who are members of the specific group chat
    that the group chat has been updated, triggering timestamp updates in the UI.

    Args:
        group_chat_id: ID of the updated group chat
    """
    group_chat = GroupChat.objects.get(id=group_chat_id)

    assert channel_layer is not None

    # Broadcast to the specific group chat's update channel
    # Only users who are members of this group will be subscribed to this channel
    group_update_channel = f"group_chat_{group_chat.pk}_updates"

    GroupChatConsumer.broadcast_event_sync(
        NotifyGroupChatUpdateEvent(
            payload=GroupChatUpdatePayload(
                group_pk=group_chat.pk,
                updated_at=group_chat.updated_at.isoformat(),
            )
        ),
        [group_update_channel],
    )
