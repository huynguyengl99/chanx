Quick Start
===========
This guide will walk you through creating a basic WebSocket endpoint with Chanx. By the end, you'll have a working WebSocket consumer that authenticates users and handles structured messages.

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
    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer

    from myapp.messages import MyIncomingMessage, EchoMessage


    class EchoConsumer(AsyncJsonWebsocketConsumer):
        """Simple echo consumer with authentication."""
        # Use DRF authentication and permissions
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        # Specify message schema for validation
        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage

        async def receive_message(self, message, **kwargs):
            """Handle incoming validated messages."""
            if message.action == "echo":
                # Echo the message back to the sender
                await self.send_message(EchoMessage(payload=f"Echo: {message.payload}"))
            elif message.action == "ping":
                # Handle ping message
                from chanx.messages.outgoing import PongMessage
                await self.send_message(PongMessage())

3. Set up WebSocket routing:

.. code-block:: python

    # myapp/routing.py
    from django.urls import re_path

    from myapp.consumers import EchoConsumer

    websocket_urlpatterns = [
        re_path(r'ws/echo/$', EchoConsumer.as_asgi()),
    ]

4. Include the routing in your ASGI application:

.. code-block:: python

    # myproject/asgi.py
    import os

    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application

    from myapp.routing import websocket_urlpatterns

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

    application = ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

Test Your WebSocket Endpoint
----------------------------
1. Start your Django development server:

.. code-block:: bash

    python manage.py runserver

2. Use the WebSocket playground (if set up) to connect and send messages:

   * Go to http://localhost:8000/chanx/playground/websocket/
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
Now let's enhance our consumer to support group messaging:

.. code-block:: python

    # myapp/consumers.py - updated
    from typing import Iterable

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        """Chat consumer with room-based groups."""
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage

        async def build_groups(self) -> Iterable[str]:
            """Build channel groups based on URL parameters."""
            # Get room_id from URL kwargs
            room_id = self.scope["url_route"]["kwargs"].get("room_id", "lobby")
            return [f"chat_{room_id}"]

        async def receive_message(self, message, **kwargs):
            """Handle incoming messages and broadcast to group."""
            if message.action == "echo":
                # Send to the whole group instead of just the sender
                await self.send_group_message(
                    EchoMessage(payload=f"{self.user.username}: {message.payload}")
                )

Update the routing:

.. code-block:: python

    # myapp/routing.py - updated
    websocket_urlpatterns = [
        re_path(r'ws/echo/$', EchoConsumer.as_asgi()),
        re_path(r'ws/chat/(?P<room_id>\w+)/$', ChatConsumer.as_asgi()),
    ]

Now you can open multiple browser windows and chat in the same room!

Next Steps
----------
Congratulations! You've created a basic WebSocket application with authentication and group messaging using Chanx.

To learn more:

* :doc:`user-guide/authentication` - Learn more about authentication options
* :doc:`user-guide/messages` - Explore the message validation system
* :doc:`user-guide/consumers` - Discover consumer configuration options
* :doc:`examples/chat` - See a complete chat application example
