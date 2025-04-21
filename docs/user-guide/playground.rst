WebSocket Playground
====================
Chanx includes a powerful WebSocket playground that provides a visual interface for exploring and testing
WebSocket endpoints. This tool makes it easier to develop, debug, and document your WebSocket APIs.

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

1. Add the playground URLs to your project's URL configuration:

.. code-block:: python

    # urls.py
    from django.urls import path, include

    urlpatterns = [
        # ...
        path('chanx/', include('chanx.playground.urls')),
        # ...
    ]

2. Ensure the playground templates and static files are accessible:

.. code-block:: python

    # settings.py
    INSTALLED_APPS = [
        # ...
        'chanx',
        # ...
    ]

3. Access the playground at ``/chanx/playground/websocket/`` in your browser

Using the Playground
--------------------
The playground interface is divided into several sections:

Endpoint Selection
^^^^^^^^^^^^^^^^^^
The left panel displays all discovered WebSocket endpoints with their URLs and descriptions. Endpoints are automatically discovered from your URL routing configuration.

.. code-block:: python

    # routing.py example that will be discovered
    from django.urls import re_path
    from myapp.consumers import ChatConsumer, NotificationConsumer

    websocket_urlpatterns = [
        re_path(r'ws/chat/(?P<room_id>\w+)/$', ChatConsumer.as_asgi()),
        re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    ]

Connection Panel
^^^^^^^^^^^^^^^^
The connection panel allows you to:

1. View the complete WebSocket URL
2. Manage path parameters for endpoints with URL parameters
3. Add authentication headers or query parameters
4. Connect and disconnect from the WebSocket

For endpoints with URL parameters (like ``room_id`` in the example above), you'll be able to enter parameter values before connecting.

Message Composer
^^^^^^^^^^^^^^^^
The message composer provides:

1. A JSON editor with syntax highlighting
2. Example message templates based on your consumer's message schema
3. A "Send" button to transmit the message

Example messages are automatically generated from your ``INCOMING_MESSAGE_SCHEMA`` class, helping you send correctly structured messages.

Message History
^^^^^^^^^^^^^^^
The message history panel shows:

1. All sent and received messages in chronological order
2. Message direction (sent/received)
3. Formatted JSON with syntax highlighting
4. Timestamps for each message

Authentication Testing
^^^^^^^^^^^^^^^^^^^^^^
The playground supports testing authenticated endpoints through:

1. Cookie-based authentication (using your browser's cookies)
2. Header-based authentication (by adding custom headers)
3. Query parameter authentication

For example, to test a token-authenticated endpoint:

1. In the headers section, add: ``Authorization: Token your_token_here``
2. Or in the URL parameters section, add: ``token=your_token_here``

Generating Example Messages
---------------------------
The playground automatically generates example messages based on your message schema:

.. code-block:: python

    from typing import Literal, Optional
    from chanx.messages.base import BaseIncomingMessage, BaseMessage


    class ChatMessage(BaseMessage):
        """Send a chat message to the room."""
        action: Literal["chat"] = "chat"
        payload: str


    class TypingMessage(BaseMessage):
        """Indicate user is typing."""
        action: Literal["typing"] = "typing"
        payload: Optional[bool] = True


    class MyChatMessages(BaseIncomingMessage):
        """Chat application messages."""
        message: ChatMessage | TypingMessage

For the consumer using this schema:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        INCOMING_MESSAGE_SCHEMA = MyChatMessages

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
            path('chanx/', include('chanx.playground.urls')),
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

Customizing the Playground
--------------------------
You can customize the playground by:

1. **Override Templates**: Create your own version of the playground template
2. **Extend Views**: Subclass the playground views to add custom behavior
3. **Custom Styling**: Add your own CSS to modify the appearance

To override the template:

1. Create a file at ``templates/playground/websocket.html`` in your project
2. Copy the original template content from the package
3. Modify as needed

Advanced Usage
--------------
**Testing Different Authentication Methods**

The playground allows you to test different authentication methods:

1. **Session Authentication**: Works automatically with your browser's cookies
2. **Token Authentication**: Add an Authorization header
3. **Basic Authentication**: Add a Basic Authentication header
4. **Custom Authentication**: Add any required headers or parameters

**Working with Binary Messages**

While the playground is designed for JSON messages, you can also work with binary data:

1. Use the "Send Binary" option if available
2. Or encode binary data in a compatible format (Base64)

**Multiple Connections**

You can open multiple playground tabs to test:

1. Group messaging between different clients
2. User-to-user messaging
3. Broadcast functionality
