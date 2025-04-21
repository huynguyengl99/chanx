from channels.routing import URLRouter
from django.urls import path

from discussion.consumers import DiscussionConsumer

router = URLRouter(
    [
        path("", DiscussionConsumer.as_asgi()),
    ]
)
