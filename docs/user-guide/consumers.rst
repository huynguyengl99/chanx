Consumers
=========
The ``AsyncJsonWebsocketConsumer`` class is the cornerstone of Chanx, providing a robust foundation for building WebSocket applications. This guide covers its features, configuration options, and best practices.

Consumer Basics
---------------
Chanx consumers extend Django Channels' WebSocket consumers with:

1. DRF-style authentication and permissions
2. Structured message handling with validation
3. Automatic group management
4. Comprehensive error handling
5. Logging and diagnostics

Minimal Consumer Example
------------------------
Here's a minimal Chanx consumer:

.. code-block:: python

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.incoming import IncomingMessage


    class MyConsumer(AsyncJsonWebsocketConsumer):
        """Basic WebSocket consumer."""

        # Required: Specify the message schema
        INCOMING_MESSAGE_SCHEMA = IncomingMessage

        async def receive_message(self, message, **kwargs):
            """Handle incoming validated messages."""
            # Handle message based on its action
            if message.action == "ping":
                from chanx.messages.outgoing import PongMessage
                await self.send_message(PongMessage())

Consumer Lifecycle
------------------
A Chanx consumer follows this lifecycle:

1. **Connection**: Client initiates WebSocket connection
2. **Authentication**: Consumer authenticates the connection using DRF classes
3. **Group Setup**: If authenticated, consumer joins channel groups
4. **Message Processing**: Consumer handles incoming messages
5. **Disconnection**: Client or server terminates the connection


Authentication Configuration
----------------------------
Configure authentication and permissions using DRF-style attributes:

.. code-block:: python

    from rest_framework.authentication import SessionAuthentication, TokenAuthentication
    from rest_framework.permissions import IsAuthenticated


    class SecureConsumer(AsyncJsonWebsocketConsumer):
        # Authentication classes determine how users are identified
        authentication_classes = [SessionAuthentication, TokenAuthentication]

        # Permission classes determine if authenticated users have access
        permission_classes = [IsAuthenticated]

        # For object-level permissions, provide a queryset
        queryset = Room.objects.all()

        # HTTP method to emulate for authentication
        auth_method = "get"  # Default is "get"

        INCOMING_MESSAGE_SCHEMA = IncomingMessage

Message Handling
----------------
The core of a consumer is the ``receive_message`` method which processes validated messages:

.. code-block:: python

    async def receive_message(self, message, **kwargs):
        """
        Handle incoming validated messages.

        Args:
            message: The validated message object
            **kwargs: Additional arguments from receive_json
        """
        # Access the action field to determine message type
        if message.action == "chat":
            # Access payload for message data
            text = message.payload

            # Create response message
            from myapp.messages import ChatResponse
            response = ChatResponse(payload=f"Received: {text}")

            # Send response to the client
            await self.send_message(response)

Group Management
----------------
Chanx simplifies WebSocket group management for pub/sub messaging:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer):

        async def build_groups(self):
            """
            Define which groups this consumer should join.

            Returns:
                Iterable of group names
            """
            # Get room ID from URL parameters
            room_id = self.scope["url_route"]["kwargs"].get("room_id", "default")

            # Return list of groups to join
            return [f"chat_room_{room_id}"]

        async def receive_message(self, message, **kwargs):
            if message.action == "chat":
                # Forward message to the entire group
                await self.send_group_message(message)

Sending Messages
----------------
Chanx provides several methods for sending messages:

.. code-block:: python

    # Send to the connected client
    await self.send_message(MyMessage())

    # Send to all clients in groups (excluding this one)
    await self.send_group_message(
        GroupMessage(),
        exclude_current=True  # Don't echo to sender
    )

    # Send to specific groups
    await self.send_group_message(
        GroupMessage(),
        groups=["custom_group"],  # Override default groups
        exclude_current=False     # Include sender
    )

Configuration Options
---------------------
Chanx consumers have several configuration options:

.. code-block:: python

    class ConfiguredConsumer(AsyncJsonWebsocketConsumer):
        # Authentication
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]
        queryset = None
        auth_method = "get"

        # Message handling
        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage
        OUTGOING_GROUP_MESSAGE_SCHEMA = MyOutgoingGroupMessage

        # Behavior flags
        send_completion = True  # Send completion messages
        send_message_immediately = True  # Yield control after sending
        log_received_message = True  # Log received messages
        log_sent_message = True  # Log sent messages
        log_ignored_actions = ["ping", "pong"]  # Don't log these actions
        send_authentication_message = True  # Send auth status

Accessing User and Context
--------------------------
Within a consumer, you can access user information and context:

.. code-block:: python

    async def receive_message(self, message, **kwargs):
        # Access the authenticated user
        user = self.user

        # Access the Django request (from authentication)
        request = self.request

        # For consumers with object-level permissions, access the object
        obj = self.obj

        # Access the raw ASGI connection scope
        scope = self.scope

        # Access URL parameters
        url_params = self.scope["url_route"]["kwargs"]

        # Access query string parameters
        query_params = parse_qs(self.scope["query_string"].decode())

Post-Authentication Hook
------------------------
You can perform custom actions after successful authentication:

.. code-block:: python

    async def post_authentication(self):
        """Execute after successful authentication."""
        # Perform custom initialization
        self.user_status = "online"

        # Record connection in database
        await self.update_user_status()

Error Handling
--------------
Chanx automatically handles most errors:

1. **Validation errors**: Sends detailed error messages to the client
2. **Processing errors**: Captures exceptions and sends generic error
3. **Authentication errors**: Closes connection with authentication failure

For custom error handling:

.. code-block:: python

    async def receive_message(self, message, **kwargs):
        try:
            result = await self.process_message(message)
            await self.send_message(SuccessMessage(payload=result))
        except ValueError as e:
            # Send custom error for specific exceptions
            await self.send_message(ErrorMessage(payload={"detail": str(e)}))
        # Other exceptions are handled automatically

Testing Consumers
-----------------
Chanx provides utilities for testing consumers:

.. code-block:: python

    from chanx.testing import WebsocketTestCase
    from myapp.messages import ChatMessage


    class TestChatConsumer(WebsocketTestCase):
        ws_path = "/ws/chat/room1/"

        async def test_chat_message(self):
            # Create and connect a websocket client
            communicator = self.create_communicator()
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Ensure authentication succeeded
            await communicator.assert_authenticated_status_ok()

            # Send a test message
            await communicator.send_message(ChatMessage(payload="Hello"))

            # Receive all messages until completion
            messages = await communicator.receive_all_json()

            # Assert on the received messages
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["payload"], "Hello")

            # Disconnect
            await communicator.disconnect()

Routing Configuration
---------------------
Chanx provides enhanced URL routing capabilities through ``chanx.urls`` and modular routing with ``chanx.routing``:

.. code-block:: python

    # routing.py
    from chanx.urls import path, re_path
    from chanx.routing import include
    from .consumers import ChatConsumer, NotificationConsumer

    # Application-specific routes
    router = URLRouter([
        # Simple path-based routing with converters
        path('<str:room_id>/', ChatConsumer.as_asgi()),

        # Regex-based routing for more complex patterns
        re_path(r'^(?P<user_id>\w+)/$', NotificationConsumer.as_asgi()),
    ])

    # In the main routing file:
    router = URLRouter([
        # Include app-specific routes
        path('chat/', include('chat.routing')),
        path('notifications/', include('notifications.routing')),
    ])

For more details on URL routing, see :doc:`../reference/urls` and :doc:`../reference/routing`.

Best Practices
--------------
1. **Use type hints**: Add proper type annotations for better IDE support
2. **Keep consumers focused**: Each consumer should handle a specific domain
3. **Document message formats**: Clearly document expected message structures
4. **Implement proper error handling**: Provide meaningful error messages
5. **Use object-level permissions**: For endpoints tied to specific resources
6. **Implement reconnection logic**: Clients should handle reconnection
7. **Test thoroughly**: Test both happy paths and error scenarios

Next Steps
----------
- :doc:`authentication` - Learn more about authentication options
- :doc:`messages` - Explore the message validation system
- :doc:`../examples/chat` - See a complete chat application example
