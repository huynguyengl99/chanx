from channels.routing import URLRouter

from chanx.routing import path

from assistants.consumers import AssistantConsumer

router = URLRouter(
    [
        path("", AssistantConsumer.as_asgi()),
    ]
)
