from channels.routing import URLRouter

from chanx.routing import path

from discussion.consumers import DiscussionConsumer

router = URLRouter(
    [
        path("", DiscussionConsumer.as_asgi()),
    ]
)
