Routing
=======
Chanx provides Django-style routing utilities specifically designed for WebSocket applications. These functions work similarly to Django's URL routing but are optimized for Channels and ASGI applications.

Key Components
--------------
Chanx's routing system includes:

1. Django-like URL pattern matching with ``path()`` and ``re_path()``
2. Modular routing with ``include()``
3. Type-safe URL converters
4. Consistent naming conventions for better organization
5. Separation between HTTP routing (``django.urls``) and WebSocket routing (``chanx.routing``)

Routing Organization
--------------------
For optimal organization, structure your routing like this:

1. Create a ``routing.py`` file in each app with WebSocket consumers
2. Name the main URLRouter variable ``router`` (similar to Django's ``urlpatterns``)
3. Create a project-level ``routing.py`` that includes app-specific routers
4. Use ``chanx.routing`` for WebSocket routes and ``django.urls`` for HTTP routes

App-Level Routing
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # chat/routing.py
    from channels.routing import URLRouter
    from chanx.routing import path, re_path

    from chat.consumers import ChatConsumer, ChatDetailConsumer

    # Important: Name this variable 'router' for string-based includes
    router = URLRouter([
        path('room/<str:room_id>/', ChatConsumer.as_asgi()),
        re_path(r'(?P<pk>\d+)/', ChatDetailConsumer.as_asgi()),
    ])

Project-Level Routing
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # myproject/routing.py
    from channels.routing import URLRouter
    from chanx.routing import path, include

    # Main router for the project
    router = URLRouter([
        # String-based include (requires router variable in chat/routing.py)
        path('chat/', include('chat.routing')),
        path('notifications/', include('notifications.routing')),
        path('assistants/', include('assistants.routing')),
    ])

ASGI Configuration
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # myproject/asgi.py
    import os
    from django.core.asgi import get_asgi_application
    from channels.routing import ProtocolTypeRouter
    from channels.security.websocket import OriginValidator
    from channels.sessions import CookieMiddleware
    from django.conf import settings

    from chanx.routing import include

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django_asgi_app = get_asgi_application()

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": OriginValidator(
            CookieMiddleware(include("myproject.routing")),
            settings.CORS_ALLOWED_ORIGINS + settings.CSRF_TRUSTED_ORIGINS,
        ),
    })

URL Patterns
------------
Chanx provides ``path()`` and ``re_path()`` functions that work exactly like Django's URL functions but are specifically designed for WebSocket routing:

.. code-block:: python

    from chanx.routing import path, re_path

    # Path with converter
    path('users/<int:user_id>/', UserConsumer.as_asgi())

    # Regular expression pattern
    re_path(r'^rooms/(?P<room_id>\w+)/$', RoomConsumer.as_asgi())

**Note**: Use ``chanx.routing`` for WebSocket endpoints and ``django.urls`` for HTTP endpoints to maintain clear separation between routing concerns.

URL Path Converters
-------------------
Chanx supports the same path converters as Django:

- ``str``: Matches any non-empty string without a slash
- ``int``: Matches zero or any positive integer
- ``slug``: Matches ASCII letters, numbers, hyphens, or underscores
- ``uuid``: Matches a formatted UUID
- ``path``: Matches any non-empty string, including slashes

.. code-block:: python

    path('rooms/<str:room_name>/', RoomConsumer.as_asgi())
    path('users/<int:user_id>/', UserConsumer.as_asgi())
    path('profiles/<slug:username>/', ProfileConsumer.as_asgi())
    path('files/<path:file_path>/', FileConsumer.as_asgi())
    path('sessions/<uuid:session_id>/', SessionConsumer.as_asgi())

Modular Routing with include()
------------------------------
The ``include()`` function lets you organize routing in a modular way:

.. code-block:: python

    from chanx.routing import include

    # Include by string reference (uses 'router' variable in the module)
    path('chat/', include('chat.routing'))

    # Include a router instance directly
    path('api/', include(api_router))

Accessing URL Parameters
------------------------
In your consumer, access URL parameters through the scope:

.. code-block:: python

    async def build_groups(self):
        # Get URL parameters
        room_id = self.scope["url_route"]["kwargs"].get("room_id")
        return [f"room_{room_id}"]

Using with Object-Level Permissions
-----------------------------------
URL parameters are automatically used for object lookup when using querysets:

.. code-block:: python

    class RoomConsumer(AsyncJsonWebsocketConsumer[Room]):
        queryset = Room.objects.all()
        permission_classes = [IsRoomMember]

        async def build_groups(self):
            # self.obj is automatically loaded from URL parameter 'pk' or 'id'
            return [f"room_{self.obj.pk}"]

Best Practices
--------------
1. **Consistent naming**: Use ``routing.py`` and name the variable ``router``
2. **Modular organization**: Group related endpoints in app-specific routing files
3. **Descriptive paths**: Use descriptive URL patterns that reflect resource hierarchy
4. **Prefer path() over re_path()**: Use path converters when possible for readability
5. **Type safety**: Use proper type hints in URL parameters
6. **Separation of concerns**: Use ``chanx.routing`` for WebSocket routes and ``django.urls`` for HTTP routes

Next Steps
----------
- :doc:`consumers` - Learn about WebSocket consumers
- :doc:`authentication` - Understand authentication with WebSockets
