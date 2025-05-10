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
    from typing import Literal, Optional

    from chanx.messages.base import BaseIncomingMessage, BaseMessage
    from chanx.messages.incoming import PingMessage


    class EchoMessage(BaseMessage):
        """Message type for echoing text."""
        action: Literal["echo"] = "echo"
        payload: str


    class MyIncomingMessage(BaseIncomingMessage):
        """Custom incoming message container."""
        message: PingMessage | EchoMessage

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

    from myapp.messages import MyIncomingMessage, EchoMessage


    class EchoConsumer(AsyncJsonWebsocketConsumer):
        """Simple echo consumer with authentication."""
        # Use DRF authentication and permissions
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        # Specify message schema for validation
        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            """Handle incoming validated messages using pattern matching."""
            match message:
                case PingMessage():
                    # Handle ping message
                    await self.send_message(PongMessage())
                case EchoMessage(payload=payload):
                    # Echo the message back to the sender
                    await self.send_message(EchoMessage(payload=f"Echo: {payload}"))
                case _:
                    pass

3. Set up WebSocket routing:

.. code-block:: python

    # myapp/routing.py
    from chanx.urls import path, re_path
    from channels.routing import URLRouter

    from myapp.consumers import EchoConsumer

    router = URLRouter([
        path('echo/', EchoConsumer.as_asgi()),
    ])

4. Create a project-level routing file for centralized WebSocket routing:

.. code-block:: python

    # myproject/routing.py
    from channels.routing import URLRouter
    from chanx.routing import include
    from chanx.urls import path

    router = URLRouter([
        path('ws/', include('myapp.routing')),
        # Add other app routing here
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

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django_asgi_app = get_asgi_application()

    # Import your WebSocket routing
    from myproject.routing import router

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": OriginValidator(
            CookieMiddleware(router),
            settings.CORS_ALLOWED_ORIGINS,
        ),
    })

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
    wscat -c ws://localhost:8000/ws/echo/ -H "Cookie: sessionid=your_session_id"

4. Send a JSON message:

.. code-block:: json

    {"action": "echo", "payload": "Hello, Chanx!"}

You should receive back:

.. code-block:: json

    {"action": "echo", "payload": "Echo: Hello, Chanx!"}

Adding Group Messaging
----------------------
Now let's enhance our consumer to support group messaging. First, we need to add group message types to our existing message schema:

1. Append group message types to ``myapp/messages.py``:

.. code-block:: python

    # Add these to myapp/messages.py (appending to existing code)
    from chanx.messages.base import BaseGroupMessage, BaseOutgoingGroupMessage


    # Define a group message type
    class ChatGroupMessage(BaseGroupMessage):
        """Message type for group chat messages."""
        action: Literal["chat_message"] = "chat_message"
        payload: str


    # Define the outgoing group message container
    class MyOutgoingGroupMessage(BaseOutgoingGroupMessage):
        """Container for outgoing group messages."""
        group_message: ChatGroupMessage

2. Update your consumer to handle group messaging:

.. code-block:: python

    # myapp/consumers.py - updated
    from typing import Any, Iterable

    from myapp.messages import (
        MyIncomingMessage,
        EchoMessage,
        MyOutgoingGroupMessage,
        ChatGroupMessage
    )

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        """Chat consumer with room-based groups."""
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        # Define both incoming and outgoing message schemas
        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage
        OUTGOING_GROUP_MESSAGE_SCHEMA = MyOutgoingGroupMessage

        async def build_groups(self) -> Iterable[str]:
            """Build channel groups based on URL parameters."""
            # Get room_id from URL kwargs
            room_id = self.scope["url_route"]["kwargs"].get("room_id", "lobby")
            return [f"chat_{room_id}"]

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            """Handle incoming messages and broadcast to group using pattern matching."""
            match message:
                case PingMessage():
                    await self.send_message(PongMessage())
                case EchoMessage(payload=payload):
                    # Convert the echo message to a chat group message
                    username = getattr(self.user, 'username', 'Anonymous')

                    # Send to the whole group
                    await self.send_group_message(
                        ChatGroupMessage(payload=f"{username}: {payload}")
                    )
                case _:
                    pass

Update the routing:

.. code-block:: python

    # myapp/routing.py - updated
    from chanx.urls import path, re_path
    from channels.routing import URLRouter

    from myapp.consumers import EchoConsumer, ChatConsumer

    router = URLRouter([
        path('echo/', EchoConsumer.as_asgi()),
        re_path(r'chat/(?P<room_id>\w+)/', ChatConsumer.as_asgi()),
    ])

Now you can open multiple browser windows and chat in the same room!

Next Steps
----------
Congratulations! You've created a basic WebSocket application with authentication and group messaging using Chanx.

To learn more:

* :doc:`user-guide/authentication` - Learn more about authentication options
* :doc:`user-guide/messages` - Explore the message validation system
* :doc:`user-guide/consumers` - Discover consumer configuration options
* :doc:`examples/chat` - See a complete chat application example
