Framework Integration
======================

Chanx provides framework-specific utilities that complement your WebSocket consumers, including Django views for AsyncAPI documentation and FastAPI integration helpers. These tools bridge the gap between your WebSocket endpoints and traditional HTTP APIs.

Django Channels Integration
---------------------------

**AsyncAPI Documentation Views**

Django provides built-in views for serving AsyncAPI documentation from your WebSocket consumers:

.. code-block:: python

    # urls.py
    from django.urls import path
    from chanx.ext.channels.views import AsyncAPISchemaView, AsyncAPIDocsView

    urlpatterns = [
        # AsyncAPI spec endpoints
        path('api/asyncapi.json', AsyncAPISchemaView.as_view(), name='asyncapi-schema'),
        path('api/asyncapi.yaml', AsyncAPISchemaView.as_view(), {'format': 'yaml'}),

        # Interactive documentation
        path('docs/websocket/', AsyncAPIDocsView.as_view(), name='asyncapi-docs'),
    ]

**Available endpoints:**

- ``/api/asyncapi.json`` - JSON format AsyncAPI spec
- ``/api/asyncapi.json?format=yaml`` - YAML format AsyncAPI spec
- ``/docs/websocket/`` - Interactive AsyncAPI documentation

**Django Authenticators**

Chanx provides Django REST Framework integration for WebSocket authentication:

.. code-block:: python

    from chanx.ext.channels.authenticator import DjangoAuthenticator
    from rest_framework.permissions import IsAuthenticated
    from myapp.models import ChatRoom

    class RoomAuthenticator(DjangoAuthenticator):
        permission_classes = [IsAuthenticated]
        queryset = ChatRoom.objects.all()  # For object-level permissions
        obj: ChatRoom  # Type hint for the authenticated object

    @channel(name="room_chat")
    class RoomChatConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = RoomAuthenticator
        authenticator: RoomAuthenticator

        async def post_authentication(self) -> None:
            # Access authenticated user and object
            user = self.authenticator.user
            room = self.authenticator.obj

            # Join room-specific group
            await self.channel_layer.group_add(f"room_{room.id}", self.channel_name)

**Configuration via Django Settings**

Configure AsyncAPI generation through Django settings:

.. code-block:: python

    # settings.py
    CHANX = {
        # AsyncAPI documentation settings
        'ASYNCAPI_TITLE': 'My WebSocket API',
        'ASYNCAPI_DESCRIPTION': 'Real-time communication endpoints',
        'ASYNCAPI_VERSION': '2.1.0',
        'ASYNCAPI_SERVER_URL': 'wss://api.myapp.com',
        'ASYNCAPI_SERVER_PROTOCOL': 'wss',
    }

FastAPI Integration
-------------------

**AsyncAPI Endpoints**

FastAPI integration provides simple view functions for AsyncAPI documentation:

.. code-block:: python

    from fastapi import FastAPI, Request
    from chanx.ext.fast_channels.views import (
        asyncapi_spec_json,
        asyncapi_spec_yaml,
        asyncapi_docs
    )

    app = FastAPI()

    # AsyncAPI configuration
    config = {
        "title": "My WebSocket API",
        "version": "1.0.0",
        "description": "Real-time WebSocket endpoints"
    }

    @app.get("/api/asyncapi.json")
    async def get_asyncapi_json(request: Request):
        return await asyncapi_spec_json(request, app, config)

    @app.get("/api/asyncapi.yaml")
    async def get_asyncapi_yaml(request: Request):
        return await asyncapi_spec_yaml(request, app, config)

    @app.get("/docs/websocket/")
    async def get_asyncapi_docs(request: Request):
        return await asyncapi_docs(request, app, config)

**Custom Authenticators**

Create custom authenticators for non-Django frameworks:

.. code-block:: python

    from chanx.core.authenticator import BaseAuthenticator
    from myapp.auth import verify_token, get_user_by_token

    class TokenAuthenticator(BaseAuthenticator):
        async def authenticate(self) -> bool:
            # Get token from query parameters or headers
            token = self.get_query_param("token") or self.get_header("authorization")

            if not token:
                return False

            # Verify token and get user
            if await verify_token(token):
                self.user = await get_user_by_token(token)
                return True

            return False

    class SecureChatConsumer(BaseConsumer):
        authenticator_class = TokenAuthenticator

----------

With framework-specific integration utilities, you have all the tools needed to incorporate WebSocket consumers into your Django or FastAPI applications:

- **Django**: AsyncAPI documentation views and DjangoAuthenticator for DRF integration
- **FastAPI**: AsyncAPI endpoint functions and custom authenticator patterns

These framework-specific extensions complement the core Chanx features to provide seamless integration with your existing web applications while maintaining framework-specific conventions and patterns.
