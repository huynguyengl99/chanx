"""
ASGI config for my_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from channels.security.websocket import OriginValidator
from channels.sessions import CookieMiddleware
from django.conf import settings
from django.core.asgi import get_asgi_application

# Due to some uvicorn config we need to put the get_asgi_application before other internal import
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django_asgi_app = get_asgi_application()  # isort: skip

from config.routing import ws_routes  # noqa

routing = {
    "http": django_asgi_app,
    "websocket": OriginValidator(
        CookieMiddleware(ws_routes),
        settings.CORS_ALLOWED_ORIGINS + settings.CSRF_TRUSTED_ORIGINS,
    ),
}

application = ProtocolTypeRouter(routing)
