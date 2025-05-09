from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

from chat.models import GroupChat
from chat.serializers import (
    GroupChatSerializer,
)
from chat.utils import name_group_chat

channel_layer = get_channel_layer()


def task_handle_new_chat_message(group_chat_id: int) -> None:
    group_chat = GroupChat.objects.get(id=group_chat_id)
    serializer = GroupChatSerializer(group_chat)
    chat_list_layer_name = name_group_chat(group_chat_id)

    assert channel_layer
    async_to_sync(channel_layer.group_send)(
        chat_list_layer_name,
        {
            "type": "notify_new_chat_message",
            "payload": serializer.validated_data,
        },
    )
