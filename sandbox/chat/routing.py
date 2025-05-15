from channels.routing import URLRouter

from chanx.routing import re_path

from chat.consumers.chat_detail import ChatDetailConsumer

router = URLRouter(
    [
        re_path(r"(?P<pk>\d+)/", ChatDetailConsumer.as_asgi()),
    ]
)
