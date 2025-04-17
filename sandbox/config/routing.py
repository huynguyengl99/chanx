from channels.routing import URLRouter
from django.urls import path

from chanx.routing import include

ws_router = URLRouter(
    [
        # Use ws_include which returns a URLRouter
        path("assistants/", include("assistants.routing")),
    ]
)

router = URLRouter(
    [
        path("ws/", ws_router),
    ]
)
