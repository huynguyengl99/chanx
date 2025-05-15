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

    from typing import Any

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import IncomingMessage, PingMessage
    from chanx.messages.outgoing import PongMessage


    class MyConsumer(AsyncJsonWebsocketConsumer):
        """Basic WebSocket consumer."""

        # Required: Specify the message schema
        INCOMING_MESSAGE_SCHEMA = IncomingMessage

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            """Handle incoming validated messages."""
            # Handle message using pattern matching
            match message:
                case PingMessage():
                    await self.send_message(PongMessage())
                case _:
                    # Handle other message types or ignore
                    pass

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

    from typing import Any

    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import IncomingMessage


    class SecureConsumer(AsyncJsonWebsocketConsumer):
        # Authentication classes determine how users are identified
        authentication_classes = [SessionAuthentication]

        # Permission classes determine if authenticated users have access
        permission_classes = [IsAuthenticated]

        # For object-level permissions, provide a queryset
        queryset = Room.objects.all()

        # HTTP method to emulate for authentication
        auth_method = "get"  # Default is "get"

        INCOMING_MESSAGE_SCHEMA = IncomingMessage

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            # Only authenticated users reach this point
            pass

Message Handling
----------------
The core of a consumer is the ``receive_message`` method which processes validated messages:

.. code-block:: python

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        """
        Handle incoming validated messages.

        Args:
            message: The validated message object
            **kwargs: Additional arguments from receive_json
        """
        # Use pattern matching for cleaner message handling
        match message:
            case ChatMessage(payload=payload):
                # Create response message
                from myapp.messages import ChatResponse
                response = ChatResponse(payload=f"Received: {payload}")

                # Send response to the client
                await self.send_message(response)
            case PingMessage():
                from chanx.messages.outgoing import PongMessage
                await self.send_message(PongMessage())
            case _:
                # Handle unknown message types
                pass

Group Messaging
----------------
Chanx simplifies WebSocket group management for pub/sub messaging.

First, define your group message types:

.. code-block:: python

    from typing import Literal
    from chanx.messages.base import BaseGroupMessage, BaseOutgoingGroupMessage

    # Define a group message type
    class ChatGroupMessage(BaseGroupMessage):
        """Message type for group chat messages."""
        action: Literal["chat_message"] = "chat_message"
        payload: str

    # Define container for outgoing group messages
    class MyChatOutgoingGroupMessage(BaseOutgoingGroupMessage):
        """Container for outgoing group messages."""
        group_message: ChatGroupMessage

Then, set up your consumer to use these group message types:

.. code-block:: python

    from typing import Any, Iterable

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        # Specify both incoming and outgoing schemas
        INCOMING_MESSAGE_SCHEMA = MyChatIncomingMessage
        OUTGOING_GROUP_MESSAGE_SCHEMA = MyChatOutgoingGroupMessage

        async def build_groups(self) -> Iterable[str]:
            """
            Define which groups this consumer should join.

            Returns:
                Iterable of group names
            """
            # Get room ID from URL parameters
            room_id = self.scope["url_route"]["kwargs"].get("room_id", "default")

            # Return list of groups to join
            return [f"chat_room_{room_id}"]

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            """Handle incoming messages and broadcast to groups."""
            match message:
                case ChatMessage(payload=payload):
                    # Using send_group_message with kind="message" (default)
                    # This requires OUTGOING_GROUP_MESSAGE_SCHEMA to be defined
                    username = getattr(self.user, 'username', 'Anonymous')
                    await self.send_group_message(
                        ChatGroupMessage(payload=f"{username}: {payload}"),
                        exclude_current=False  # Include sender in recipients
                    )
                case _:
                    pass

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

    # Send as raw JSON (bypassing OUTGOING_GROUP_MESSAGE_SCHEMA)
    await self.send_group_message(
        GroupMessage(),
        kind="json",              # Send as raw JSON (default is "message")
    )

Using Generic Type Parameters
-----------------------------
Chanx consumers support generic type parameters for object-level permissions:

.. code-block:: python

    from typing import Any
    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chat.models import GroupChat

    # Specify the model type for better type checking and IDE support
    class ChatDetailConsumer(AsyncJsonWebsocketConsumer[GroupChat]):
        queryset = GroupChat.objects.get_queryset()
        permission_classes = [IsGroupChatMember]

        async def build_groups(self) -> list[str]:
            # self.obj is now properly typed as GroupChat
            assert self.obj
            return [f"chat_{self.obj.pk}"]

        async def post_authentication(self) -> None:
            assert self.user is not None
            assert self.obj
            # Access relationships with proper typing
            self.member = await self.obj.members.select_related("user").aget(user=self.user)

Routing Configuration
---------------------
Chanx provides enhanced URL routing capabilities for WebSocket endpoints. For details, see the :doc:`routing` documentation.

Here's a brief example:

.. code-block:: python

    # chat/routing.py
    from channels.routing import URLRouter
    from chanx.routing import path, re_path
    from chat.consumers import ChatConsumer

    router = URLRouter([
        path('<str:room_id>/', ChatConsumer.as_asgi()),
    ])

    # myproject/routing.py
    from chanx.routing import include

    router = URLRouter([
        path('chat/', include('chat.routing')),
    ])

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

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
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
        from urllib.parse import parse_qs
        query_params = parse_qs(self.scope["query_string"].decode())

Post-Authentication Hook
------------------------
You can perform custom actions after successful authentication:

.. code-block:: python

    async def post_authentication(self) -> None:
        """Execute after successful authentication."""
        # Perform custom initialization
        self.user_status = "online"

        # Record connection in database
        await self.update_user_status()

        # For object-based consumers, access the object
        if self.obj:
            # Initialize object-specific state
            self.room = self.obj
            self.member = await self.room.members.aget(user=self.user)

Error Handling
--------------
Chanx automatically handles most errors:

1. **Validation errors**: Sends detailed error messages to the client
2. **Processing errors**: Captures exceptions and sends generic error
3. **Authentication errors**: Closes connection with authentication failure

For custom error handling:

.. code-block:: python

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        try:
            match message:
                case ChatMessage(payload=payload):
                    result = await self.process_chat(payload)
                    await self.send_message(SuccessMessage(payload=result))
                case _:
                    pass
        except ValueError as e:
            # Send custom error for specific exceptions
            from chanx.messages.outgoing import ErrorMessage
            await self.send_message(ErrorMessage(payload={"detail": str(e)}))
        # Other exceptions are handled automatically

Real-World Example
------------------
Here's a complete example of a chat consumer:

.. code-block:: python

    from typing import Any, cast

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    from chat.messages.chat import (
        ChatIncomingMessage,
        JoinGroupMessage,
        NewChatMessage,
    )
    from chat.messages.group import MemberMessage, OutgoingGroupMessage
    from chat.models import ChatMember, ChatMessage, GroupChat
    from chat.permissions import IsGroupChatMember
    from chat.serializers import ChatMessageSerializer
    from chat.utils import name_group_chat


    class ChatDetailConsumer(AsyncJsonWebsocketConsumer[GroupChat]):
        INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage
        OUTGOING_GROUP_MESSAGE_SCHEMA = OutgoingGroupMessage
        permission_classes = [IsGroupChatMember]
        queryset = GroupChat.objects.get_queryset()

        member: ChatMember
        groups: list[str]

        async def build_groups(self) -> list[str]:
            assert self.obj
            self.group_name = name_group_chat(self.obj.pk)
            return [self.group_name]

        async def post_authentication(self) -> None:
            assert self.user is not None
            assert self.obj
            self.member = await self.obj.members.select_related("user").aget(user=self.user)

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            match message:
                case PingMessage():
                    await self.send_message(PongMessage())
                case NewChatMessage(payload=message_payload):
                    assert self.obj
                    new_message = await ChatMessage.objects.acreate(
                        content=message_payload.content,
                        group_chat_id=self.obj.pk,
                        sender=self.member,
                    )
                    groups = message_payload.groups

                    message_serializer = ChatMessageSerializer(instance=new_message)

                    await self.send_group_message(
                        MemberMessage(payload=cast(Any, message_serializer.data)),
                        groups=groups,
                        exclude_current=False,
                    )
                case JoinGroupMessage(payload=join_group_payload):
                    await self.channel_layer.group_add(
                        join_group_payload.group_name, self.channel_name
                    )
                    self.groups.extend(join_group_payload.group_name)
                case _:
                    pass

Best Practices
--------------
1. **Use type hints**: Add proper type annotations for better IDE support
2. **Use pattern matching**: Handle messages with clear match/case patterns
3. **Keep consumers focused**: Each consumer should handle a specific domain
4. **Document message formats**: Clearly document expected message structures
5. **Implement proper error handling**: Provide meaningful error messages
6. **Use object-level permissions**: For endpoints tied to specific resources
7. **Define group message schemas**: Always define OUTGOING_GROUP_MESSAGE_SCHEMA when using group messaging
8. **Include appropriate assertions**: Use assert for type-checking in async methods
9. **Test thoroughly**: Test both happy paths and error scenarios

Next Steps
----------
- :doc:`authentication` - Learn more about authentication options
- :doc:`messages` - Explore the message validation system
- :doc:`routing` - Understand WebSocket URL routing
- :doc:`testing` - Learn how to test your consumers
- :doc:`../examples/chat` - See a complete chat application example
