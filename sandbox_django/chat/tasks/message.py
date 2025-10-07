from typing import Any, cast

from channels.layers import get_channel_layer

from chat.consumers.chat_detail import ChatDetailConsumer
from chat.messages.chat import NewChatMessageEvent
from chat.models import ChatMessage
from chat.serializers import ChatMessageSerializer
from chat.tasks import task_handle_group_chat_update
from chat.utils import name_group_chat

channel_layer = get_channel_layer()


def task_handle_new_chat_message(message_id: int) -> None:
    """
    Handle broadcasting a new chat message to all group members.

    This function:
    1. Sends the message to all members of the specific group chat
    2. Updates the group chat's last activity timestamp
    3. Notifies users about the updated timestamp for the group chat list

    Args:
        message_id: ID of the new ChatMessage to broadcast
    """
    # Get the message with all related objects
    assert channel_layer is not None

    message = ChatMessage.objects.select_related("group_chat", "sender__user").get(
        id=message_id
    )
    group_chat = message.group_chat

    # Update the group chat's last activity timestamp
    group_chat.update_last_activity()

    # Serialize the message
    serializer = ChatMessageSerializer(message)
    serialized_data = cast(dict[str, Any], serializer.data)

    # Get the group chat channel name
    chat_group = name_group_chat(group_chat.pk)

    # Send the message to the specific group chat members
    ChatDetailConsumer.broadcast_event_sync(
        NewChatMessageEvent(
            payload=NewChatMessageEvent.Payload(
                user_pk=message.sender.user.pk if message.sender else None,
                message_data=serialized_data,
            )
        ),
        [chat_group],
    )

    task_handle_group_chat_update(group_chat.pk)
