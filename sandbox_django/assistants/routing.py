from channels.routing import URLRouter

from chanx.ext.channels.routing import re_path

from assistants.consumers import (
    ConversationAssistantConsumer,
)

router = URLRouter(
    [
        # Both authenticated and anonymous users with specific conversation
        # The consumer will determine if it's authenticated or anonymous based on user state
        re_path(r"(?P<pk>[0-9a-f-]+)/", ConversationAssistantConsumer.as_asgi()),
    ]
)
