from channels.routing import URLRouter
from django.urls import path

from chat.consumers import ChatConsumer

router = URLRouter(
    [
        path("", ChatConsumer.as_asgi()),
    ]
)
