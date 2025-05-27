WebSocket Playground
====================
Chanx includes a powerful WebSocket playground that provides a visual interface for exploring and testing
WebSocket endpoints. This tool makes it easier to develop, debug, and document your WebSocket APIs.

.. image:: /_static/pg-header.png
   :alt: WebSocket Playground Header
   :width: 100%
   :align: center

Features
--------
The WebSocket playground offers several key features:

1. **Endpoint Discovery**: Automatically discovers all available WebSocket endpoints
2. **Interactive Connection**: Connect to endpoints with customizable parameters
3. **Message Composer**: Create and send structured JSON messages
4. **Message History**: View all sent and received messages with syntax highlighting
5. **Authentication Testing**: Test endpoints with different authentication methods
6. **Example Messages**: Generate example messages based on your schema definitions

Enabling the Playground
-----------------------
To enable the WebSocket playground in your project:

1. Add 'chanx.playground' to your INSTALLED_APPS:

.. code-block:: python

    # settings.py
    INSTALLED_APPS = [
        # ...
        'rest_framework',
        'channels',
        'chanx.playground',  # Add this for the WebSocket playground
        # ...
    ]

2. Add the playground URLs to your project's URL configuration:

.. code-block:: python

    # urls.py
    from django.urls import path, include

    urlpatterns = [
        # ...
        path('playground/', include('chanx.playground.urls')),
        # ...
    ]

3. Access the playground at ``/playground/websocket/`` in your browser

Using the Playground
--------------------
The playground interface is divided into several sections:

Endpoint Selection
^^^^^^^^^^^^^^^^^^
The left panel displays all discovered WebSocket endpoints with their URLs and descriptions. Endpoints are automatically discovered from your URL routing configuration.

.. code-block:: python

    # routing.py example that will be discovered
    from channels.routing import URLRouter
    from chanx.routing import path, re_path
    from myapp.consumers import ChatConsumer, NotificationConsumer

    # Important: name this variable 'router'
    router = URLRouter([
        path('chat/<str:room_id>/', ChatConsumer.as_asgi()),
        path('notifications/', NotificationConsumer.as_asgi()),
    ])

Connection Panel
^^^^^^^^^^^^^^^^
The connection panel allows you to:

1. View the complete WebSocket URL
2. Manage path parameters for endpoints with URL parameters
3. Add authentication headers or query parameters
4. Connect and disconnect from the WebSocket

.. image:: /_static/pg-header.png
   :alt: Connection Panel
   :width: 100%
   :align: center

For endpoints with URL parameters (like ``room_id`` in the example above), you'll be able to enter parameter values before connecting.

Message Composer
^^^^^^^^^^^^^^^^
The message composer provides:

1. A JSON editor with syntax highlighting
2. Example message templates based on your consumer's message schema
3. A "Send" button to transmit the message

.. image:: /_static/pg-msg.png
   :alt: Message Composer
   :width: 100%
   :align: center

Example messages are automatically generated from your consumer's message schema, helping you send correctly structured messages.

Message History
^^^^^^^^^^^^^^^
The message history panel shows:

1. All sent and received messages in chronological order
2. Message direction (sent/received)
3. Formatted JSON with syntax highlighting
4. Timestamps for each message

.. image:: /_static/pg-history.png
   :alt: Message History
   :width: 100%
   :align: center

Authentication Testing
^^^^^^^^^^^^^^^^^^^^^^
The playground supports testing authenticated endpoints through:

1. Cookie-based authentication (using your browser's cookies)
2. Query parameter authentication (for token-based auth)

For example, to test a token-authenticated endpoint using query parameters:

1. Click the "Query Params" tab
2. Add a parameter with key "token" and your token as the value
3. Connect to the WebSocket

Since browsers don't allow custom headers for WebSocket connections, cookie-based authentication is the most reliable method for testing in the playground.

Generating Example Messages
---------------------------
The playground automatically generates example messages based on your message schema:

.. code-block:: python

    from typing import Literal
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage


    class ChatMessage(BaseMessage):
        """Send a chat message to the room."""
        action: Literal["chat"] = "chat"
        payload: str


    class TypingMessage(BaseMessage):
        """Indicate user is typing."""
        action: Literal["typing"] = "typing"
        payload: bool = True


    # Define a union type for the incoming messages
    ChatIncomingMessage = ChatMessage | TypingMessage | PingMessage

For the consumer using this schema:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage]):
        # Message schema is specified as a generic parameter

The playground will generate these example messages:

.. code-block:: json

    // ChatMessage example
    {
        "action": "chat",
        "payload": "Sample message text"
    }

    // TypingMessage example
    {
        "action": "typing",
        "payload": true
    }

    // PingMessage example
    {
        "action": "ping",
        "payload": null
    }

These examples help you understand the expected message format and quickly test your endpoints.

Security Considerations
-----------------------
The WebSocket playground should be used cautiously in production environments:

1. **Disable in Production**: Consider disabling the playground in production
2. **Restrict Access**: If enabled in production, use authentication to restrict access
3. **CORS Settings**: Be aware of your CORS settings when using the playground
4. **Sensitive Data**: Avoid sending sensitive data through the playground

To disable the playground in production:

.. code-block:: python

    # urls.py
    from django.urls import path, include
    from django.conf import settings

    urlpatterns = [
        # ...
    ]

    if settings.DEBUG:
        # Only add playground URLs in development
        urlpatterns += [
            path('playground/', include('chanx.playground.urls')),
        ]

Or restrict access with a decorator:

.. code-block:: python

    # Custom playground URLs
    from django.urls import path
    from django.contrib.admin.views.decorators import staff_member_required
    from chanx.playground.views import WebSocketPlaygroundView, WebSocketInfoView

    urlpatterns = [
        path(
            'admin/websocket/',
            staff_member_required(WebSocketPlaygroundView.as_view()),
            name='websocket_playground'
        ),
        path(
            'admin/websocket-info/',
            staff_member_required(WebSocketInfoView.as_view()),
            name='websocket_info'
        ),
    ]

Testing Different Authentication Methods
----------------------------------------
The playground has been designed to work with browser constraints regarding WebSocket authentication:

1. **Session Authentication**: Works automatically with your browser's cookies
2. **JWT in Cookies**: Store JWT tokens in cookies for easy testing
3. **Query Parameters**: Add tokens or other authentication data as query parameters

For example, to authenticate with a JWT cookie:

1. Log in through your regular application interface
2. Navigate to the playground (cookies will be included automatically)
3. Connect to the authenticated endpoint

For query parameter authentication:

1. Click the "Query Params" tab in the Connection panel
2. Add your authentication parameter (e.g., "token")
3. Connect with the parameter included in the WebSocket URL

Multiple Connections
--------------------
You can open multiple playground tabs to test:

1. Group messaging between different clients
2. User-to-user messaging
3. Broadcast functionality

Simply open the playground in multiple browser tabs, potentially with different user sessions, and connect to the same WebSocket endpoint.

Next Steps
----------
- :doc:`authentication` - Learn more about WebSocket authentication
- :doc:`messages` - Understand message formats and validation
- :doc:`testing` - See how to automate WebSocket testing
