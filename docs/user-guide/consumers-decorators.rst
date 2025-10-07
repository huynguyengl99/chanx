Consumers & Decorators
======================

Chanx transforms WebSocket development with decorator-based message handlers that automatically route messages, validate types, and generate documentation. This guide covers the core patterns you'll use to build WebSocket applications.

The AsyncJsonWebsocketConsumer Base Class
-----------------------------------------

All Chanx consumers inherit from ``AsyncJsonWebsocketConsumer``, which provides the foundation for decorator-based message handling:

.. code-block:: python

    from chanx.core.websocket import AsyncJsonWebsocketConsumer
    from chanx.core.decorators import ws_handler, event_handler, channel

    @channel(name="chat", description="Real-time chat system")
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        # Your handlers go here
        pass

**Optional Generic Type Parameter:**

You can optionally specify an event type for better static type checking with mypy/pyright:

.. code-block:: python

    # Without generic type (perfectly fine)
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        pass

    # With generic type for enhanced type checking
    class ChatConsumer(AsyncJsonWebsocketConsumer[SystemNotifyEvent]):
        pass

The generic type parameter helps with:

- **Type safety** for ``send_event()``, ``broadcast_event()`` methods
- **Better IDE support** with autocomplete and type hints
- **Static analysis** with mypy/pyright

**Note:** The generic type is purely optional and for developer convenience. It doesn't affect runtime behavior or functionality.

**Key features provided by the base class:**

- **Automatic message routing** based on decorators
- **Type validation** using Pydantic discriminated unions
- **Channel layer integration** for group messaging
- **Authentication handling** with configurable authenticators
- **Completion signals** for reliable testing
- **Configurable behavior** via class attributes

The @channel Decorator
----------------------

The ``@channel`` decorator marks consumer classes and provides metadata for AsyncAPI documentation generation:

.. code-block:: python

    @channel(
        name="notifications",
        description="User notification system",
        tags=["notifications", "real-time"]
    )
    class NotificationConsumer(AsyncJsonWebsocketConsumer):
        pass

**Parameters:**

- **name** (str, optional): Custom channel name (defaults to class name)
- **description** (str, optional): Channel description (overrides class docstring)
- **tags** (list[str], optional): Tags for AsyncAPI grouping

The @ws_handler Decorator
-------------------------

The ``@ws_handler`` decorator handles messages sent directly from WebSocket clients. Each handler method corresponds to a specific message type:

.. code-block:: python

    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    @channel(name="example")
    class ExampleConsumer(AsyncJsonWebsocketConsumer):
        @ws_handler(summary="Handle ping requests")
        async def handle_ping(self, message: PingMessage) -> PongMessage:
            return PongMessage()

        @ws_handler(
            summary="Handle chat messages",
            description="Process chat messages and broadcast to room members",
            output_type=ChatNotificationMessage,
            tags=["chat", "messaging"]
        )
        async def handle_chat(self, message: ChatMessage) -> None:
            # Broadcast to group instead of direct response
            await self.broadcast_message(
                ChatNotificationMessage(
                    payload=ChatPayload(
                        message=f"User: {message.payload.message}"
                    )
                )
            )

**Handler patterns:**

**1. Direct Response (return message):**

.. code-block:: python

    @ws_handler
    async def handle_ping(self, message: PingMessage) -> PongMessage:
        return PongMessage()  # Sent directly back to client

**2. Broadcast Response (return None):**

.. code-block:: python

    @ws_handler(output_type=NotificationMessage)
    async def handle_broadcast(self, message: BroadcastMessage) -> None:
        await self.broadcast_message(
            NotificationMessage(payload="Broadcasted to all")
        )

**3. No Response:**

.. code-block:: python

    @ws_handler
    async def handle_log_event(self, message: LogMessage) -> None:
        logger.info(f"Received: {message.payload}")
        # No response sent

**@ws_handler parameters:**

- **func**: The handler function (when used without parentheses)
- **action** (str, optional): Action name (defaults to function name)
- **input_type** (type, optional): Expected input message type
- **output_type** (type, optional): Expected output message type for docs
- **summary** (str, optional): Brief description for AsyncAPI
- **description** (str, optional): Detailed description for AsyncAPI
- **tags** (list[str], optional): Tags for AsyncAPI grouping

The @event_handler Decorator
----------------------------

The ``@event_handler`` decorator handles events sent through the channel layer from other parts of your application (HTTP views, background tasks, management scripts, etc.):

.. code-block:: python

    @event_handler(output_type=StreamingMessage)
    async def handle_streaming(self, event: StreamingEvent) -> StreamingMessage:
        """Handle streaming events from background tasks."""
        return StreamingMessage(payload=event.payload)

    @event_handler
    async def user_joined_room(self, event: UserJoinedEvent) -> None:
        """Handle user join events without direct response."""
        await self.broadcast_message(
            SystemMessage(payload=f"{event.payload.username} joined")
        )

**@event_handler return patterns:**

- **Return message**:
  - If triggered by ``send_event()`` → sends to the specific channel (WebSocket connection)
  - If triggered by ``broadcast_event()`` → broadcasts the message to all channels in the target groups
- **Return None**: Use for custom behavior - you can manually broadcast, send to specific channels, or perform side effects

**@event_handler parameters:**

- **func**: The handler function (when used without parentheses)
- **input_type** (type, optional): Expected event type for validation
- **output_type** (type, optional): Expected output type for docs
- **summary** (str, optional): Brief description for AsyncAPI
- **description** (str, optional): Detailed description for AsyncAPI
- **tags** (list[str], optional): Tags for AsyncAPI grouping

Message Types and Automatic Routing
-----------------------------------

Chanx uses **discriminated unions** to automatically route both WebSocket messages and events to the correct handlers. Messages and events are identified by their ``action`` field:

**WebSocket Message Example:**

.. code-block:: python

    from chanx.messages.base import BaseMessage
    from typing import Literal

    class ChatMessage(BaseMessage):
        action: Literal["chat"] = "chat"  # Discriminator field
        payload: ChatPayload

    class PingMessage(BaseMessage):
        action: Literal["ping"] = "ping"
        payload: None = None

**Event Message Example:**

.. code-block:: python

    class UserJoinedEvent(BaseMessage):
        action: Literal["user_joined"] = "user_joined"  # Discriminator field
        payload: UserPayload

    class SystemNotifyEvent(BaseMessage):
        action: Literal["system_notify"] = "system_notify"
        payload: NotificationPayload

**How routing works:**

**For WebSocket messages:**
1. Client sends: ``{"action": "chat", "payload": {"message": "Hello"}}``
2. Framework validates against discriminated union of all input messages
3. Routes to ``@ws_handler`` method based on message type
4. Handler receives properly typed message object

**For events:**
1. Application sends: ``Consumer.send_event(UserJoinedEvent(...))``
2. Framework validates against discriminated union of all event types
3. Routes to ``@event_handler`` method based on event type
4. Handler receives properly typed event object

**The framework automatically:**

- Builds separate discriminated unions for WebSocket messages and events
- Validates incoming JSON/events against the appropriate union
- Routes to the correct handler method (``@ws_handler`` or ``@event_handler``)
- Provides full type safety with IDE support for both message types

Output Messages and Broadcasting
---------------------------------

**Direct Response Messages:**

.. code-block:: python

    @ws_handler
    async def handle_get_status(self, message: GetStatusMessage) -> StatusMessage:
        return StatusMessage(
            payload=StatusPayload(
                status="online",
                timestamp=datetime.now()
            )
        )

**Broadcasting Messages:**

.. code-block:: python

    @ws_handler(output_type=ChatNotificationMessage)
    async def handle_chat(self, message: ChatMessage) -> None:
        # Broadcast to all connections in the same groups
        await self.broadcast_message(
            ChatNotificationMessage(payload=message.payload)
        )

        # Broadcast to specific groups
        await self.broadcast_message(
            ChatNotificationMessage(payload=message.payload),
            groups=["room_123", "moderators"]
        )

**Group Management:**

.. code-block:: python

    class RoomChatConsumer(AsyncJsonWebsocketConsumer):
        async def post_authentication(self) -> None:
            """Called after successful authentication."""
            # Extract room from URL parameters
            room_id = self.scope["path_params"]["room_id"]
            group_name = f"room_{room_id}"

            # Join the room group
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.groups.append(group_name)

            # Notify others about the join
            await self.broadcast_message(
                UserJoinedMessage(payload={"user_id": self.user.id}),
                groups=[group_name],
                exclude_current=True  # Don't send to self
            )

Event Broadcasting from Anywhere
---------------------------------

One of Chanx's most powerful features is sending events to WebSocket consumers from anywhere in your application:

**From Django Views:**

.. code-block:: python

    # views.py
    from django.http import JsonResponse
    from myapp.consumers import NotificationConsumer
    from myapp.events import NewPostEvent

    def create_post(request):
        post = Post.objects.create(...)

        # Send event to WebSocket consumers
        NotificationConsumer.broadcast_event_sync(
            NewPostEvent(payload={"post_id": post.id, "title": post.title}),
            groups=["news_feed"]
        )

        return JsonResponse({"status": "created"})

**From Celery Tasks:**

.. code-block:: python

    # tasks.py
    from celery import shared_task
    from myapp.consumers import PaymentConsumer
    from myapp.events import PaymentCompleteEvent

    @shared_task
    def process_payment(payment_id):
        result = process_payment_logic(payment_id)

        # Notify specific user
        PaymentConsumer.send_event_sync(
            PaymentCompleteEvent(payload={"status": result}),
            channel_name=f"user_{payment.user_id}"
        )

**From Management Commands:**

.. code-block:: python

    # management/commands/send_announcement.py
    from django.core.management.base import BaseCommand
    from myapp.consumers import AnnouncementConsumer

    class Command(BaseCommand):
        def add_arguments(self, parser):
            parser.add_argument('message', type=str)

        def handle(self, *args, **options):
            AnnouncementConsumer.broadcast_event_sync(
                SystemAnnouncementEvent(payload=options['message']),
                groups=["all_users"]
            )

**Available event methods:**

- **send_event_sync()**: Send to specific channel name
- **broadcast_event_sync()**: Send to groups
- **send_event()**: Async version of send_event_sync
- **broadcast_event()**: Async version of broadcast_event_sync

**Note:** When using the optional generic type parameter (``AsyncJsonWebsocketConsumer[EventType]``), these methods will provide better type checking and IDE support for the event parameter.

Consumer Configuration
----------------------

Consumers can be configured via class attributes:

.. code-block:: python

    class MyConsumer(AsyncJsonWebsocketConsumer):
        # Message behavior
        send_completion = False  # Whether to send completion signals
        send_message_immediately = True  # Yield control after sending
        log_websocket_message = True  # Log messages
        log_ignored_actions = ["ping", "pong"]  # Skip logging these

        # Message formatting
        camelize = False  # Convert snake_case <-> camelCase
        discriminator_field = "action"  # Field for message routing

        # Channel layer (required for non-Django frameworks)
        channel_layer_alias = "default"

        # Authentication
        authenticator_class = MyAuthenticator

Authentication Integration
--------------------------

**Django Example:**

.. code-block:: python

    from chanx.ext.channels.authenticator import DjangoAuthenticator
    from rest_framework.permissions import IsAuthenticated

    class ChatAuthenticator(DjangoAuthenticator):
        permission_classes = [IsAuthenticated]
        # Optional: object-level permissions
        queryset = ChatRoom.objects.all()
        obj: ChatRoom

    @channel(name="chat")
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = ChatAuthenticator
        authenticator: ChatAuthenticator  # Type hint

        async def post_authentication(self) -> None:
            """Called after successful authentication."""
            # Access authenticated user and object
            user = self.authenticator.user
            room = self.authenticator.obj  # If using object-level auth

            # Join room-specific group
            await self.channel_layer.group_add(
                f"room_{room.id}",
                self.channel_name
            )

**FastAPI/Custom Example:**

.. code-block:: python

    from chanx.core.authenticator import BaseAuthenticator

    class TokenAuthenticator(BaseAuthenticator):
        async def authenticate(self) -> bool:
            token = self.get_query_param("token")
            if not token:
                return False

            # Validate token logic here
            self.user = await get_user_by_token(token)
            return self.user is not None

    class MyConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = TokenAuthenticator

Complete Example: Chat Consumer
-------------------------------

Here's a complete example that demonstrates all the concepts:

.. code-block:: python

    from chanx.core.decorators import ws_handler, event_handler, channel
    from chanx.core.websocket import AsyncJsonWebsocketConsumer
    from chanx.ext.channels.authenticator import DjangoAuthenticator
    from rest_framework.permissions import IsAuthenticated

    # Messages
    class ChatMessage(BaseMessage):
        action: Literal["chat"] = "chat"
        payload: ChatPayload

    class JoinRoomMessage(BaseMessage):
        action: Literal["join_room"] = "join_room"
        payload: JoinRoomPayload

    # Events
    class UserJoinedEvent(BaseChannelEvent):
        handler: Literal["user_joined"] = "user_joined"
        payload: UserPayload

    # Authenticator
    class RoomAuthenticator(DjangoAuthenticator):
        permission_classes = [IsAuthenticated]
        queryset = ChatRoom.objects.all()
        obj: ChatRoom

    # Consumer (generic type is optional - either approach works)
    @channel(
        name="room_chat",
        description="Real-time chat for specific rooms",
        tags=["chat", "rooms"]
    )
    class RoomChatConsumer(AsyncJsonWebsocketConsumer[UserJoinedEvent]):  # Optional generic for type hints
        authenticator_class = RoomAuthenticator
        authenticator: RoomAuthenticator

        # Configuration
        log_ignored_actions = ["ping", "pong"]

        async def post_authentication(self) -> None:
            """Join room group after authentication."""
            room_group = f"room_{self.authenticator.obj.id}"
            await self.channel_layer.group_add(room_group, self.channel_name)
            self.groups.append(room_group)

        @ws_handler(
            summary="Handle chat messages",
            output_type=ChatNotificationMessage
        )
        async def handle_chat(self, message: ChatMessage) -> None:
            """Process and broadcast chat messages."""
            await self.broadcast_message(
                ChatNotificationMessage(
                    payload=ChatNotificationPayload(
                        message=message.payload.message,
                        username=self.authenticator.user.username,
                        room_id=self.authenticator.obj.id
                    )
                )
            )

        @event_handler(output_type=UserJoinedMessage)
        async def user_joined(self, event: UserJoinedEvent) -> UserJoinedMessage:
            """Handle user join events from other parts of the app."""
            return UserJoinedMessage(
                payload=UserJoinedPayload(
                    username=event.payload.username,
                    message=f"{event.payload.username} joined the room"
                )
            )

Next Steps
----------

Now that you understand Chanx's decorator-based approach, you can:

- Learn about :doc:`asyncapi` documentation generation
- Explore :doc:`testing` patterns for WebSocket consumers
- Check out :doc:`framework-integration` for Django views and FastAPI API endpoints

The decorator pattern eliminates the complexity of manual message routing while providing full type safety and automatic documentation generation. This makes WebSocket development as straightforward as building REST APIs.
