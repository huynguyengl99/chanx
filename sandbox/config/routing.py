from channels.routing import URLRouter
from django.urls import path, re_path

from chanx.routing import include

ws_router = URLRouter(
    [
        # Use ws_include which returns a URLRouter
        path("assistants/", include("assistants.routing")),
        path("discussion/", include("discussion.routing")),
        re_path("chat/", include("chat.routing")),
    ]
)

router = URLRouter(
    [
        re_path("ws/", ws_router),
    ]
)
