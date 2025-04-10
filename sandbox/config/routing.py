from channels.routing import URLRouter
from django.urls import path

from sandbox_app.routing import routes

ws_all_routes = URLRouter([*routes])

ws_routes = URLRouter(
    [
        path("ws/", ws_all_routes),
    ]
)
