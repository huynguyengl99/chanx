Quick Start
===========
This guide will walk you through creating a basic WebSocket endpoint with Chanx. By the end, you'll have a working WebSocket consumer that authenticates users and handles structured messages.

Project Setup
-------------
Before creating WebSocket consumers, let's set up the required Django Channels infrastructure:

1. Configure a channel layer in your Django settings:

.. code-block:: python

    # settings.py
    INSTALLED_APPS = [
        # ...
        'rest_framework',
        'channels',
        'chanx.playground',  # Add this for the WebSocket playground
        # ...
    ]

    ASGI_APPLICATION = "myproject.asgi.application"

    # Redis channel layer (recommended for production)
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("127.0.0.1", 6379)],
            },
        },
    }

    # In-memory channel layer (for development/testing)
    # CHANNEL_LAYERS = {
    #     "default": {
    #         "BACKEND": "channels.layers.InMemoryChannelLayer"
    #     },
    # }

2. Configure allowed origins for WebSocket connections:

.. code-block:: python

    # settings.py
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8000",
        # Add other trusted origins
    ]

3. Set up the WebSocket playground:

.. code-block:: python

    # urls.py
    from django.urls import path, include

    urlpatterns = [
        # ...
        path('playground/', include('chanx.playground.urls')),
        # ...
    ]

Create a Simple Echo Consumer
-----------------------------
Let's create a basic echo consumer that authenticates users and echoes back messages.

1. First, create a custom message schema:

.. code-block:: python

    # myapp/messages.py
    from typing import Literal

    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage
    from pydantic import BaseModel


    class MessagePayload(BaseModel):
        content: str


    class EchoMessage(BaseMessage):
        """Message type for echoing text."""
        action: Literal["echo"] = "echo"
        payload: MessagePayload


    # Define a union of all supported message types
    MyIncomingMessage = EchoMessage | PingMessage

2. Create a WebSocket consumer:

.. code-block:: python

    # myapp/consumers.py
    from typing import Any
    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    from myapp.messages import MyIncomingMessage, EchoMessage, MessagePayload


    class EchoConsumer(AsyncJsonWebsocketConsumer[MyIncomingMessage]):
        """Simple echo consumer with authentication."""
        # Use DRF authentication and permissions
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        async def receive_message(self, message: MyIncomingMessage, **kwargs: Any) -> None:
            """Handle incoming validated messages using pattern matching."""
            match message:
                case PingMessage():
                    # Handle ping message
                    await self.send_message(PongMessage())
                case EchoMessage(payload=payload):
                    # Echo the message back to the sender
                    await self.send_message(EchoMessage(payload=MessagePayload(content=f"Echo: {payload.content}")))

3. Set up WebSocket routing:

.. code-block:: python

    # myapp/routing.py
    from chanx.routing import path
    from channels.routing import URLRouter

    from myapp.consumers import EchoConsumer

    router = URLRouter([
        path('echo/', EchoConsumer.as_asgi()),
    ])

4. Create a project-level routing file for centralized WebSocket routing:

.. code-block:: python

    # myproject/routing.py
    from chanx.routing import include, path
    from channels.routing import URLRouter

    router = URLRouter([
        path('ws/', URLRouter([
            path('myapp/', include('myapp.routing')),
            # Add other app routing here
        ])),
    ])

5. Configure your ASGI application to use the WebSocket routing:

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

    routing = {
        "http": django_asgi_app,
        "websocket": OriginValidator(
            CookieMiddleware(include("myproject.routing")),
            settings.CORS_ALLOWED_ORIGINS + settings.CSRF_TRUSTED_ORIGINS,
        ),
    }

    application = ProtocolTypeRouter(routing)

Test Your WebSocket Endpoint
----------------------------
1. Start your Django development server:

.. code-block:: bash

    python manage.py runserver

2. Use the WebSocket playground (if set up) to connect and send messages:

   * Go to http://localhost:8000/playground/websocket/
   * Select your echo endpoint
   * Connect to the WebSocket
   * Send a message with action "echo" and a payload

3. Or use a WebSocket client like wscat:

.. code-block:: bash

    # First, get a valid session cookie by logging in through the browser
    # Then use that cookie with wscat
    wscat -c ws://localhost:8000/ws/myapp/echo/ -H "Cookie: sessionid=your_session_id"

4. Send a JSON message:

.. code-block:: json

    {"action": "echo", "payload": {"content": "Hello, Chanx!"}}

You should receive back:

.. code-block:: json

    {"action": "echo", "payload": {"content": "Echo: Hello, Chanx!"}}

Adding Group Messaging
----------------------
Now let's enhance our consumer to support group messaging. First, we need to add group message types:

1. Add group message types to ``myapp/messages.py``:

.. code-block:: python

    # Add these to myapp/messages.py (appending to existing code)
    from chanx.messages.base import BaseGroupMessage


    # Define a group message type
    class ChatGroupMessage(BaseGroupMessage):
        """Message type for group chat messages."""
        action: Literal["chat_message"] = "chat_message"
        payload: MessagePayload

2. Update your consumer to handle group messaging:

.. code-block:: python

    # myapp/consumers.py - updated
    from typing import Any, Iterable

    from myapp.messages import (
        MyIncomingMessage,
        EchoMessage,
        MessagePayload,
        ChatGroupMessage
    )

    class ChatConsumer(AsyncJsonWebsocketConsumer[MyIncomingMessage, None, ChatGroupMessage]):
        """Chat consumer with room-based groups."""
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        async def build_groups(self) -> Iterable[str]:
            """Build channel groups based on URL parameters."""
            # Get room_id from URL kwargs
            room_id = self.scope["url_route"]["kwargs"].get("room_id", "lobby")
            return [f"chat_{room_id}"]

        async def receive_message(self, message: MyIncomingMessage, **kwargs: Any) -> None:
            """Handle incoming messages and broadcast to group using pattern matching."""
            match message:
                case PingMessage():
                    await self.send_message(PongMessage())
                case EchoMessage(payload=payload):
                    # Convert the echo message to a chat group message
                    username = getattr(self.user, 'username', 'Anonymous')

                    # Send to the whole group
                    await self.send_group_message(
                        ChatGroupMessage(
                            payload=MessagePayload(content=f"{username}: {payload.content}")
                        )
                    )
                case _:
                    pass

Update the routing:

.. code-block:: python

    # myapp/routing.py - updated
    from chanx.routing import path, re_path
    from channels.routing import URLRouter

    from myapp.consumers import EchoConsumer, ChatConsumer

    router = URLRouter([
        path('echo/', EchoConsumer.as_asgi()),
        re_path(r'chat/(?P<room_id>\w+)/', ChatConsumer.as_asgi()),
    ])

Now you can open multiple browser windows and chat in the same room!

Adding Channel Events
---------------------
Let's add support for system notifications using channel events:

1. Add event types to ``myapp/messages.py``:

.. code-block:: python

    # Add these to myapp/messages.py
    from chanx.messages.base import BaseChannelEvent

    class NotifyEvent(BaseChannelEvent):
        """Event for sending notifications to connected clients."""
        class Payload(BaseModel):
            content: str
            level: str = "info"

        handler: Literal["notify"] = "notify"
        payload: Payload

    # Define event union type
    ChatEvent = NotifyEvent

2. Update your consumer to handle events:

.. code-block:: python

    # myapp/consumers.py - updated further
    class ChatConsumer(AsyncJsonWebsocketConsumer[MyIncomingMessage, ChatEvent, ChatGroupMessage]):
        """Chat consumer with room-based groups and event handling."""
        # Add ChatEvent as the second generic parameter

        # ... existing code ...

        async def receive_event(self, event: ChatEvent) -> None:
            """Handle channel events using pattern matching."""
            match event:
                case NotifyEvent():
                    notification = f"{event.payload.level.upper()}: {event.payload.content}"

                    # Send to the connected client
                    await self.send_message(
                        EchoMessage(payload=MessagePayload(content=notification))
                    )

3. Create a view to send notifications:

.. code-block:: python

    # myapp/serializers.py
    from rest_framework import serializers


    class NotificationSerializer(serializers.Serializer):
        """Serializer for notification data."""
        message = serializers.CharField(
            max_length=500,
            help_text="The notification message content"
        )
        level = serializers.ChoiceField(
            choices=[
                ('info', 'Info'),
                ('warning', 'Warning'),
                ('error', 'Error'),
                ('success', 'Success'),
            ],
            default='info',
            help_text="The notification level/severity"
        )

.. code-block:: python

    # myapp/views.py
    from rest_framework import status
    from rest_framework.decorators import api_view, permission_classes
    from rest_framework.permissions import IsAuthenticated
    from rest_framework.response import Response

    from myapp.consumers import ChatConsumer
    from myapp.messages import NotifyEvent
    from myapp.serializers import NotificationSerializer


    @api_view(['POST'])
    def send_notification(request, room_id):
        """
        Send a notification to all users in a room.
        """
        serializer = NotificationSerializer(data=request.data)

        if serializer.is_valid():
            # Send event to the channel layer
            ChatConsumer.send_channel_event(
                f"chat_{room_id}",
                NotifyEvent(
                    payload=NotifyEvent.Payload(
                        content=serializer.validated_data['message'],
                        level=serializer.validated_data['level']
                    )
                )
            )

            return Response({
                "status": "sent",
                "room_id": room_id,
                "message": serializer.validated_data['message'],
                "level": serializer.validated_data['level']
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

4. Add the view to your URLs:

.. code-block:: python

    # myapp/urls.py
    from django.urls import path
    from . import views

    urlpatterns = [
        path('api/notify/<str:room_id>/', views.send_notification, name='notify_room'),
    ]


5. Test the notification API:

.. code-block:: bash

    # Send a notification via the API
    curl -X POST http://localhost:8000/api/notify/lobby/ \
      -H "Content-Type: application/json" \
      -d '{
        "message": "Welcome to the chat room!",
        "level": "info"
      }'

Now you can send notifications to all users in a room via an API endpoint!

Next Steps
----------
Congratulations! You've created a WebSocket application with authentication, group messaging, and channel events using Chanx. To learn more:

* :doc:`user-guide/authentication` - Learn more about authentication options
* :doc:`user-guide/messages` - Explore the message validation system
* :doc:`user-guide/consumers` - Discover consumer configuration options
* :doc:`examples/chat` - See a complete chat application example
