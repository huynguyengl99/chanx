from channels.routing import URLRouter

from chanx.channels.routing import path, re_path

from chat.consumers.chat_detail import ChatDetailConsumer
from chat.consumers.group import GroupChatConsumer

router = URLRouter(
    [
        path("group/", GroupChatConsumer.as_asgi()),
        re_path(r"(?P<pk>\d+)/", ChatDetailConsumer.as_asgi()),
    ]
)
