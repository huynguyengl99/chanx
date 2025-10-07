Consumers
=========
The ``AsyncJsonWebsocketConsumer`` class is the cornerstone of Chanx, providing a robust foundation for building WebSocket applications. This guide covers its features, configuration options, and best practices.

Consumer Basics
---------------
Chanx consumers extend Django Channels' WebSocket consumers with:

1. DRF-style authentication and permissions
2. Structured message handling with validation
3. Automatic group management
4. Typed channel events
5. Comprehensive error handling
6. Logging and diagnostics

Minimal Consumer Example
------------------------
Here's a minimal Chanx consumer:

.. code-block:: python

    from typing import Any

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage


    class MyConsumer(AsyncJsonWebsocketConsumer[PingMessage]):
        """Basic WebSocket consumer."""

        async def receive_message(self, message: PingMessage, **kwargs: Any) -> None:
            """Handle incoming validated messages."""
            # Handle message using pattern matching
            match message:
                case PingMessage():
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

    from typing import Any

    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chat.models import Room


    class SecureConsumer(AsyncJsonWebsocketConsumer[PingMessage, None, Room]):
        # Authentication classes determine how users are identified
        authentication_classes = [SessionAuthentication]

        # Permission classes determine if authenticated users have access
        permission_classes = [IsAuthenticated]

        # For object-level permissions, provide a queryset
        queryset = Room.objects.all()

        # HTTP method to emulate for authentication
        auth_method = "get"  # Default is "get"

        async def receive_message(self, message: PingMessage, **kwargs: Any) -> None:
            # Only authenticated users reach this point
            pass

Generic Type Parameters
-----------------------
Chanx consumers support three generic type parameters for improved type safety:

.. code-block:: python

    class AsyncJsonWebsocketConsumer(Generic[IC, Event, M]):
        """
        Base WebSocket consumer with generic type parameters.

        Generic Parameters:
            IC: Incoming message type (required) - Union of BaseMessage subclasses
            Event: Channel event type (optional) - Union of BaseChannelEvent subclasses or None
            M: Model type for object-level permissions (optional) - Model subclass or None
        """

At minimum, you must specify the incoming message type:

.. code-block:: python

    # Simple consumer with just incoming message type
    class SimpleConsumer(AsyncJsonWebsocketConsumer[PingMessage]):
        ...

    # Consumer with events
    class EventConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage, ChatEvent]):
        ...

    # Full consumer with all generic parameters
    class FullConsumer(AsyncJsonWebsocketConsumer[
        ChatIncomingMessage,       # Incoming message types
        ChatEvent,                 # Channel events
        Room                       # Model for object permissions
    ]):
        ...

Message Handling
-----------------
The core of a consumer is the ``receive_message`` method which processes validated messages:

.. code-block:: python

    async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
        """
        Process a validated received message.

        Args:
            message: The validated message object (typed as ChatIncomingMessage)
            **kwargs: Additional arguments from receive_json
        """
        # Use pattern matching for cleaner message handling
        match message:
            case ChatMessage(payload=payload):
                # Handle chat message with extracted payload
                await self.handle_chat(payload)

            case NotificationMessage(payload=notification_payload):
                # Handle notification with direct access to payload
                await self.handle_notification(notification_payload)

            case PingMessage():
                # Handle standard ping message
                await self.send_message(PongMessage())


Sending Messages
----------------
To send a message to the connected client:

.. code-block:: python

    # Create a message instance with structured payload
    notification = NotificationMessage(payload={"type": "info", "text": "Update received"})

    # Send it to the client
    await self.send_message(notification)

Group Messaging
---------------
Chanx simplifies WebSocket group management for pub/sub messaging.

First, define your group message types:

.. code-block:: python

    from typing import Literal
    from chanx.messages.base import BaseGroupMessage

    # Define a group message type
    class ChatGroupMessage(BaseGroupMessage):
        """Message type for group chat."""
        action: Literal["chat_group"] = "chat_group"
        payload: dict[str, str]

Then, configure your consumer to handle group messaging:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage]):
        async def build_groups(self) -> list[str]:
            """
            Define which groups this consumer should join.

            Returns:
                Iterable of group names
            """
            # Get room ID from URL parameters
            room_id = self.scope["url_route"]["kwargs"].get("room_id", "default")

            # Return list of groups to join
            return [f"chat_room_{room_id}"]

        async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
            """Handle incoming messages and broadcast to groups."""
            match message:
                case ChatMessage(payload=payload):
                    # Using broadcast_message
                    username = getattr(self.user, 'username', 'Anonymous')
                    await self.broadcast_message(
                        ChatGroupMessage(payload={"username": username, "content": payload.content}),
                        exclude_current=False  # Include sender in recipients
                    )
                case _:
                    pass

Group messages are automatically enhanced with metadata:

.. code-block:: json

    {
      "action": "chat_group",
      "payload": {
        "username": "Alice",
        "content": "Hello everyone!"
      },
      "is_mine": false,
      "is_current": false
    }

- ``is_mine``: True if the message originated from the current user
- ``is_current``: True if the message came from this specific connection

Channel Events
--------------
Chanx provides a type-safe channel event system for sending events between consumers through the channel layer:

.. code-block:: python

    from typing import Literal
    from chanx.messages.base import BaseChannelEvent
    from pydantic import BaseModel

    # Define channel event types
    class NotifyEvent(BaseChannelEvent):
        class Payload(BaseModel):
            content: str
            level: str = "info"

        handler: Literal["notify"] = "notify"
        payload: Payload

    # Define event union type
    ChatEvent = NotifyEvent  # Can be a union of multiple event types

Configure your consumer to handle these events:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage, ChatEvent]):
        # Configure groups to receive events
        groups = ["announcements"]

        # Override receive_event method to handle all event types
        async def receive_event(self, event: ChatEvent) -> None:
            """Handle channel events using pattern matching."""
            match event:
                case NotifyEvent():
                    notification = f"{event.payload.level.upper()}: {event.payload.content}"
                    await self.send_message(MessageResponse(payload={"text": notification}))

To send events from outside the consumer (e.g., from a Django view or task):

.. code-block:: python

    # Using synchronous code (e.g., in a Django view)
    def send_notification(request):
        ChatConsumer.send_event_sync(
            "announcements",  # Group name to send to
            NotifyEvent(payload=NotifyEvent.Payload(
                content="Important system notice",
                level="warning"
            ))
        )
        return JsonResponse({"status": "sent"})

    # Using asynchronous code
    async def async_send_notification():
        await ChatConsumer.send_event(
            "announcements",
            NotifyEvent(payload=NotifyEvent.Payload(
                content="Important system notice",
                level="warning"
            ))
        )

The channel event system provides:

1. Type-safe event handling with Pydantic validation
2. Single method override (``receive_event``) for handling all event types
3. Pattern matching for different event types within the method
4. Automatic error handling and logging
5. Support for both sync and async code
6. Completion messages (if configured)

Accessing User and Context
--------------------------
Within a consumer, you can access user information and context:

.. code-block:: python

    async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
        # Access the authenticated user
        user = self.user

        # Access the Django request (from authentication)
        request = self.request

        # For consumers with object-level permissions, access the object
        obj = self.obj  # Typed based on M generic parameter

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

    async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
        try:
            match message:
                case ChatMessage(payload=payload):
                    result = await self.process_chat(payload)
                    await self.send_message(SuccessMessage(payload=result))
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
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    from chat.messages.chat import (
        ChatIncomingMessage,
        JoinGroupMessage,
        NewChatMessage,
    )
    from chat.messages.group import MemberMessage
    from chat.models import ChatMember, ChatMessage, GroupChat
    from chat.permissions import IsGroupChatMember
    from chat.serializers import ChatMessageSerializer
    from chat.utils import name_group_chat


    class ChatDetailConsumer(
        AsyncJsonWebsocketConsumer[ChatIncomingMessage, None, GroupChat]
    ):
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

        async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
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

                    await self.broadcast_message(
                        MemberMessage(payload=cast(Any, message_serializer.data)),
                        groups=groups,
                        exclude_current=False,
                    )
                case JoinGroupMessage(payload=join_group_payload):
                    await self.channel_layer.group_add(
                        join_group_payload.group_name, self.channel_name
                    )
                    self.groups.extend(join_group_payload.group_name)


Configuration Options
---------------------
Chanx consumers have several configuration options:

.. code-block:: python

    class ConfiguredConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage]):
        # Authentication
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated]
        queryset = Room.objects.all()
        auth_method = "get"

        # Behavior flags
        send_completion = True  # Send completion messages
        send_message_immediately = True  # Yield control after sending
        log_received_message = True  # Log received messages
        log_sent_message = True  # Log sent messages
        log_ignored_actions = ["ping", "pong"]  # Don't log these actions
        send_authentication_message = True  # Send auth status

Best Practices
--------------
1. **Use generic type parameters**: Specify the message, event, and model types for better IDE support
2. **Use pattern matching**: Handle messages with clear match/case patterns
3. **Keep consumers focused**: Each consumer should handle a specific domain
4. **Document message formats**: Clearly document expected message structures
5. **Implement proper error handling**: Provide meaningful error messages
6. **Use object-level permissions**: For endpoints tied to specific resources
7. **Include appropriate assertions**: Use assert for type-checking in async methods
8. **Test thoroughly**: Test both happy paths and error scenarios

Next Steps
----------
- :doc:`authentication` - Learn more about authentication options
- :doc:`messages` - Explore the message validation system
- :doc:`routing` - Understand WebSocket URL routing
- :doc:`testing` - Learn how to test your consumers
- :doc:`../examples/chat` - See a complete chat application example
