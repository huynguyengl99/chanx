from channels.routing import URLRouter

from chanx.urls import path

from assistants.consumers import AssistantConsumer

router = URLRouter(
    [
        path("", AssistantConsumer.as_asgi()),
    ]
)
