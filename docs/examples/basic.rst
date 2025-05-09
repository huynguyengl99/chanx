Basic Example
=============
This example demonstrates a simple WebSocket application using Chanx. It includes an echo service with authentication and structured messages, showing the fundamental features of the framework.

Project Setup
-------------
First, let's create a basic Django project structure:

.. code-block:: bash

    myproject/
    ├── manage.py
    ├── myproject/
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    └── echo/
        ├── __init__.py
        ├── consumers.py
        ├── messages.py
        ├── routing.py
        └── templates/
            └── echo/
                └── index.html

Message Types
-------------
Define message types in `echo/messages.py`:

.. code-block:: python

    from typing import Literal, Optional

    from chanx.messages.base import BaseIncomingMessage, BaseMessage
    from chanx.messages.incoming import PingMessage


    class EchoMessage(BaseMessage):
        """Message for echoing text back to the client."""
        action: Literal["echo"] = "echo"
        payload: str


    class StatusMessage(BaseMessage):
        """Message for sending status updates."""
        action: Literal["status"] = "status"
        payload: str


    class EchoIncomingMessage(BaseIncomingMessage):
        """Container for incoming message types."""
        message: PingMessage | EchoMessage

WebSocket Consumer
------------------
Create a consumer in `echo/consumers.py`:

.. code-block:: python

    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.outgoing import PongMessage

    from echo.messages import EchoIncomingMessage, EchoMessage, StatusMessage


    class EchoConsumer(AsyncJsonWebsocketConsumer):
        """
        Simple echo consumer that responds to messages.

        Demonstrates basic authentication and message handling with Chanx.
        """
        # Authentication setup
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]

        # Message schema
        INCOMING_MESSAGE_SCHEMA = EchoIncomingMessage

        # Enable completion messages
        send_completion = True

        async def post_authentication(self) -> None:
            """Actions after successful authentication."""
            # Send a welcome message after connection authentication
            user = self.user
            await self.send_message(
                StatusMessage(payload=f"Welcome, {user.username}!")
            )

        async def receive_message(self, message, **kwargs):
            """Handle incoming messages."""
            # Handle different message types based on action
            if message.action == "ping":
                # Respond to ping with pong
                await self.send_message(PongMessage())

            elif message.action == "echo":
                # Echo the message back with the user's name
                user = self.user
                echo_text = f"{user.username}: {message.payload}"
                await self.send_message(EchoMessage(payload=echo_text))

WebSocket Routing
-----------------
Set up routing in `echo/routing.py`:

.. code-block:: python

    from django.urls import re_path

    from echo.consumers import EchoConsumer

    websocket_urlpatterns = [
        re_path(r"ws/echo/$", EchoConsumer.as_asgi()),
    ]

ASGI Configuration
------------------
Configure the ASGI application in `myproject/asgi.py`:

.. code-block:: python

    import os

    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application

    from echo.routing import websocket_urlpatterns

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

    application = ProtocolTypeRouter(
        {
            "http": get_asgi_application(),
            "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        }
    )

Settings Configuration
----------------------
Update `myproject/settings.py` with Channels and Chanx settings:

.. code-block:: python

    INSTALLED_APPS = [
        # Django apps
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        # Third-party apps
        "channels",
        "rest_framework",
        "chanx",
        # Local apps
        "echo",
    ]

    # Channels configuration
    ASGI_APPLICATION = "myproject.asgi.py:application"

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
            # For production, use Redis:
            # "BACKEND": "channels_redis.core.RedisChannelLayer",
            # "CONFIG": {
            #     "hosts": [("127.0.0.1", 6379)],
            # },
        }
    }

    # Chanx settings
    CHANX = {
        "SEND_COMPLETION": True,
        "SEND_AUTHENTICATION_MESSAGE": True,
        "LOG_RECEIVED_MESSAGE": True,
        "LOG_SENT_MESSAGE": True,
    }

HTML Template
-------------
Create a simple frontend in `echo/templates/echo/index.html`:

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        <title>Chanx Echo Example</title>
        <style>
            #chat-log {
                width: 100%;
                height: 300px;
                border: 1px solid #ccc;
                overflow-y: scroll;
                padding: 10px;
                margin-bottom: 20px;
            }
            .received {
                color: blue;
            }
            .sent {
                color: green;
            }
            .status {
                color: #888;
                font-style: italic;
            }
            .error {
                color: red;
            }
        </style>
    </head>
    <body>
        <h1>Chanx Echo Example</h1>
        <div id="chat-log"></div>
        <div>
            <input type="text" id="message-input" placeholder="Type a message...">
            <button id="send-button">Send</button>
            <button id="ping-button">Ping</button>
        </div>

        <script>
            // Get elements
            const chatLog = document.getElementById('chat-log');
            const messageInput = document.getElementById('message-input');
            const sendButton = document.getElementById('send-button');
            const pingButton = document.getElementById('ping-button');

            // WebSocket setup
            let socket;

            function connect() {
                // Determine WebSocket URL (ws:// or wss://)
                const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
                const host = window.location.host;
                const wsUrl = `${protocol}${host}/ws/echo/`;

                // Create WebSocket connection
                socket = new WebSocket(wsUrl);

                // Connection opened
                socket.addEventListener('open', (event) => {
                    addMessage('Connected to WebSocket', 'status');
                });

                // Listen for messages
                socket.addEventListener('message', (event) => {
                    const data = JSON.parse(event.data);
                    console.log('Message from server:', data);

                    // Handle different message types
                    switch (data.action) {
                        case 'echo':
                            addMessage(`Echo: ${data.payload}`, 'received');
                            break;
                        case 'status':
                            addMessage(`Status: ${data.payload}`, 'status');
                            break;
                        case 'pong':
                            addMessage('Received pong response', 'received');
                            break;
                        case 'authentication':
                            handleAuthentication(data);
                            break;
                        case 'error':
                            handleError(data);
                            break;
                        case 'complete':
                            // Optional: Handle completion message
                            break;
                        default:
                            addMessage(`Unknown message type: ${data.action}`, 'status');
                    }
                });

                // Connection closed
                socket.addEventListener('close', (event) => {
                    addMessage('Disconnected from WebSocket', 'status');

                    // Try to reconnect after 3 seconds
                    setTimeout(connect, 3000);
                });

                // Connection error
                socket.addEventListener('error', (event) => {
                    addMessage('WebSocket error occurred', 'error');
                    console.error('WebSocket error:', event);
                });
            }

            // Handle authentication messages
            function handleAuthentication(data) {
                const status = data.payload.status_code;
                const statusText = data.payload.status_text;

                if (status === 200) {
                    addMessage(`Authentication successful: ${statusText}`, 'status');
                } else {
                    addMessage(`Authentication failed: ${statusText}`, 'error');
                    addMessage('Please login to use this feature', 'error');
                }
            }

            // Handle error messages
            function handleError(data) {
                addMessage(`Error: ${JSON.stringify(data.payload)}`, 'error');
            }

            // Add message to chat log
            function addMessage(message, type) {
                const messageElement = document.createElement('div');
                messageElement.textContent = message;
                messageElement.classList.add(type);
                chatLog.appendChild(messageElement);

                // Scroll to bottom
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            // Send echo message
            function sendEchoMessage() {
                const message = messageInput.value.trim();

                if (message && socket.readyState === WebSocket.OPEN) {
                    // Create echo message
                    const echoMessage = {
                        action: 'echo',
                        payload: message
                    };

                    // Send the message
                    socket.send(JSON.stringify(echoMessage));

                    // Add to chat log
                    addMessage(`Sent: ${message}`, 'sent');

                    // Clear input field
                    messageInput.value = '';
                }
            }

            // Send ping message
            function sendPingMessage() {
                if (socket.readyState === WebSocket.OPEN) {
                    // Create ping message
                    const pingMessage = {
                        action: 'ping'
                    };

                    // Send the message
                    socket.send(JSON.stringify(pingMessage));

                    // Add to chat log
                    addMessage('Sent: ping', 'sent');
                }
            }

            // Event listeners
            sendButton.addEventListener('click', sendEchoMessage);

            messageInput.addEventListener('keypress', (event) => {
                if (event.key === 'Enter') {
                    sendEchoMessage();
                }
            });

            pingButton.addEventListener('click', sendPingMessage);

            // Connect when page loads
            document.addEventListener('DOMContentLoaded', connect);
        </script>
    </body>
    </html>

Django View
-----------
Create a view to render the template in `echo/views.py`:

.. code-block:: python

    from django.contrib.auth.decorators import login_required
    from django.shortcuts import render


    @login_required
    def echo_view(request):
        """Render the echo application page."""
        return render(request, "echo/index.html")

URL Configuration
-----------------
Add the view to your URL configuration in `myproject/urls.py`:

.. code-block:: python

    from django.contrib import admin
    from django.urls import path, include

    from echo import views

    urlpatterns = [
        path("admin/", admin.site.urls),
        # Echo application view
        path("echo/", views.echo_view, name="echo"),
        # Add the playground for development
        path("chanx/", include("chanx.playground.urls")),
    ]

Testing the Consumer
--------------------
Let's write a test for our consumer in `echo/tests.py`:

.. code-block:: python

    from django.contrib.auth.models import User

    from chanx.testing import WebsocketTestCase
    from echo.messages import EchoMessage


    class EchoConsumerTests(WebsocketTestCase):
        """Tests for the EchoConsumer."""

        ws_path = "/ws/echo/"

        def setUp(self):
            super().setUp()
            # Create test user
            self.user = User.objects.create_user(
                username="testuser",
                password="testpassword"
            )

            # Log in with the test client
            self.client.login(username="testuser", password="testpassword")

        def get_ws_headers(self):
            """Provide session cookie for WebSocket authentication."""
            cookies = self.client.cookies
            return [
                (b"cookie", f"sessionid={cookies['sessionid'].value}".encode()),
            ]

        async def test_echo_message(self):
            """Test sending and receiving echo messages."""
            # Create a WebSocket communicator
            communicator = self.create_communicator()

            # Connect to the WebSocket
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Verify authentication succeeded
            await communicator.assert_authenticated_status_ok()

            # Should receive welcome message
            welcome = await communicator.receive_json_from()
            self.assertEqual(welcome["action"], "status")
            self.assertIn("Welcome", welcome["payload"])

            # Skip completion message
            await communicator.receive_json_from()

            # Send an echo message
            test_message = "Hello, world!"
            await communicator.send_message(EchoMessage(payload=test_message))

            # Receive the echo response
            response = await communicator.receive_json_from()

            # Verify the response
            self.assertEqual(response["action"], "echo")
            self.assertEqual(response["payload"], f"testuser: {test_message}")

            # Disconnect
            await communicator.disconnect()

Running the Example
-------------------
1. Install the dependencies:

   .. code-block:: bash

       pip install django djangorestframework channels chanx

2. Run migrations:

   .. code-block:: bash

       python manage.py migrate

3. Create a superuser:

   .. code-block:: bash

       python manage.py createsuperuser

4. Start the development server:

   .. code-block:: bash

       python manage.py runserver

5. Access the application:

   - Login page: http://localhost:8000/admin/login/
   - Echo application: http://localhost:8000/echo/
   - WebSocket playground: http://localhost:8000/chanx/playground/websocket/

Key Concepts Demonstrated
-------------------------
This example demonstrates several key Chanx features:

1. **Authentication**: Using SessionAuthentication to secure WebSocket connections
2. **Message Schemas**: Defining structured message types with Pydantic validation
3. **Consumer Lifecycle**: Handling connection, authentication, and messages
4. **Message Handling**: Processing different message types based on the action field
5. **Testing**: Using WebsocketTestCase to test WebSocket consumers
6. **Frontend Integration**: Building a simple JavaScript client

Extensions and Next Steps
-------------------------
To build on this example, you could:

1. **Add Group Messaging**: Implement broadcast functionality to all connected clients
2. **Implement User Status**: Track and display online/offline status of users
3. **Add Message History**: Store messages in a database and provide history on connection
4. **Create Multiple Rooms**: Support multiple chat rooms with separate channels
5. **Add Message Validation**: Implement more complex message validation with Pydantic

For a more complex example, see the :doc:`chat` application that builds on these concepts.
