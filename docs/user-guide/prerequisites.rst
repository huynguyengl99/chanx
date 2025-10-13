Prerequisites
=============

Before diving into Chanx, it's helpful to understand some fundamental concepts about WebSocket development and the infrastructure that powers real-time communication in web applications.

What are WebSocket Consumers?
-----------------------------

A **WebSocket consumer** is a handler that manages the lifecycle of a WebSocket connection. Think of it as a controller for a specific WebSocket endpoint - similar to how an HTTP view handles HTTP requests, a consumer handles WebSocket connections and messages.

**Key responsibilities of a consumer:**

- **Connection management**: Accept/reject connections, handle disconnections
- **Message handling**: Process incoming messages from clients
- **Message sending**: Send responses or broadcasts back to clients
- **Group management**: Add/remove connections to/from broadcast groups

**Example consumer lifecycle:**

.. code-block:: python

    # 1. Client connects -> consumer.connect()
    # 2. Client sends message -> consumer.receive()
    # 3. Consumer processes and responds
    # 4. Consumer may broadcast to groups
    # 5. Client disconnects -> consumer.disconnect()

What are Channel Layers?
------------------------

A **channel layer** is a communication system that allows different parts of your application to send messages to WebSocket consumers, even from outside the WebSocket connection context.

**Why channel layers matter:**

- **Cross-process communication**: Send messages from HTTP views, background tasks, or other processes
- **Group broadcasting**: Send messages to multiple WebSocket connections simultaneously
- **Decoupled architecture**: Separate message generation from message delivery

**Common use cases:**

.. code-block:: python

    # From an HTTP view
    def create_post(request):
        post = Post.objects.create(...)

        # Notify all connected WebSocket clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "news_updates",
            {"type": "post.created", "post_id": post.id}
        )
        return JsonResponse({"status": "created"})

    # From a Celery task
    @celery.task
    def process_payment(payment_id):
        result = process_payment_logic(payment_id)

        # Notify the user's WebSocket connection
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.send)(
            f"user_{user_id}",
            {"type": "payment.completed", "status": result}
        )

**Channel layer backends:**

- **Redis**: Production-ready, supports horizontal scaling
- **In-memory**: Development/testing only, single process
- **RabbitMQ**: Alternative message broker option

Channel Layer Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Django Channels setup:**

.. code-block:: python

    # settings.py
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("127.0.0.1", 6379)],
            },
        },
    }

**FastAPI/other frameworks setup:**

You'll need to configure your channel layer separately and reference it in your consumers:

.. code-block:: python

    # Configure Redis connection
    import redis
    from channels_redis.core import RedisChannelLayer

    channel_layer = RedisChannelLayer(hosts=[("localhost", 6379)])

    # Reference in consumer
    class BaseConsumer(AsyncJsonWebsocketConsumer):
        channel_layer_alias = "default"  # Required for non-Django

WebSocket vs HTTP: Key Differences
----------------------------------

Understanding these differences helps you design better real-time applications:

**HTTP Characteristics:**

- Request-response cycle
- Stateless connections
- One response per request
- Client always initiates

**WebSocket Characteristics:**

- Persistent bi-directional connections
- Stateful - connection remains open
- Multiple messages in both directions
- Either party can initiate communication

**This means WebSockets are ideal for:**

- Live chat applications
- Real-time notifications
- Live data feeds (stock prices, sports scores)
- Collaborative editing
- Gaming applications
- Live progress updates

Message Types in WebSocket Applications
---------------------------------------

WebSocket applications typically handle two types of messages:

**1. Direct Client Messages**
Messages sent directly from WebSocket clients to the consumer:

.. code-block:: javascript

    // Client sends
    websocket.send(JSON.stringify({
        "action": "chat_message",
        "payload": {"message": "Hello everyone!"}
    }));

**2. Channel Layer Events**
Messages sent from other parts of your application via the channel layer:

.. code-block:: python

    # From anywhere in your app
    channel_layer.group_send("chat_room", {
        "type": "user_joined",
        "username": "alice"
    })

**Chanx handles both types with decorators:**

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        @ws_handler  # Handles direct client messages
        async def handle_chat(self, message: ChatMessage) -> None:
            await self.broadcast_message(...)

        @event_handler  # Handles channel layer events
        async def user_joined(self, event: UserJoinedEvent) -> None:
            await self.send_message(...)

Groups and Broadcasting
-----------------------

**Groups** are a powerful concept for managing message broadcasting to multiple connections:

**Group membership:**

.. code-block:: python

    # Add connection to a group
    await self.channel_layer.group_add("chat_room", self.channel_name)

    # Remove from group
    await self.channel_layer.group_discard("chat_room", self.channel_name)

**Broadcasting to groups:**

.. code-block:: python

    # Send to everyone in the group
    await self.channel_layer.group_send("chat_room", {
        "type": "chat.message",
        "message": "Hello everyone!"
    })

**Common group patterns:**

- ``room_{room_id}`` - Chat rooms, game sessions
- ``user_{user_id}`` - User-specific notifications
- ``admin_users`` - Admin broadcast groups
- ``location_{city}`` - Location-based groups

Authentication in WebSocket Applications
----------------------------------------

WebSocket authentication differs from HTTP because:

- **No built-in session handling** - WebSockets don't automatically carry session cookies
- **Long-lived connections** - Authentication happens once at connection time
- **Custom header handling** - Need to extract tokens from headers or query params

**Common authentication patterns:**

.. code-block:: javascript

    // Token in query parameters
    // ws://localhost:8000/ws/chat/?token=abc123

    // Token in headers
    const socket = new WebSocket('ws://localhost:8000/ws/chat/', [], {
        headers: {'Authorization': 'Bearer abc123'}
    });

**Chanx provides authenticators to handle this:**

.. code-block:: python

    class MyAuthenticator(DjangoAuthenticator):
        permission_classes = [IsAuthenticated]

    class MyConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = MyAuthenticator

What Chanx Adds
---------------

Now that you understand the foundation concepts, here's what Chanx brings to WebSocket development:

**1. Eliminates Manual Routing**
No more giant if/else statements - decorators automatically route messages:

.. code-block:: python

    # Instead of manual routing
    async def receive_json(self, content):
        action = content.get("action")
        if action == "chat":
            await self.handle_chat(content)
        elif action == "ping":
            await self.handle_ping(content)
        # ... many more elif statements

    # Chanx uses clean decorators
    @ws_handler
    async def handle_chat(self, message: ChatMessage) -> None: ...

    @ws_handler
    async def handle_ping(self, message: PingMessage) -> PongMessage: ...

**2. Automatic Type Safety**
Pydantic message validation with discriminated unions:

.. code-block:: python

    class ChatMessage(BaseMessage):
        action: Literal["chat"] = "chat"
        payload: ChatPayload

    # Framework automatically validates and routes

**3. Multi-Framework Support**
Same API works across Django, FastAPI, and other ASGI frameworks with automatic framework detection.

**4. Automatic Documentation**
AsyncAPI 3.0 specs generated directly from your decorated handlers.

**5. Enhanced Testing**
Specialized testing utilities with completion signals for reliable WebSocket tests.

Ready for Chanx?
----------------

Now that you understand the foundational concepts, you're ready to see how Chanx transforms WebSocket development. The next guide covers :doc:`consumers-decorators` where you'll learn the decorator-based patterns that make WebSocket development as clean as building REST APIs.

Key takeaways:

- **Consumers** handle WebSocket connections like HTTP views handle requests
- **Channel layers** enable communication from anywhere in your application
- **Groups** provide powerful broadcasting capabilities
- **Authentication** requires special handling for long-lived connections
- **Chanx** eliminates boilerplate and adds type safety, documentation, and testing tools

Continue to :doc:`consumers-decorators` to start building with Chanx's decorator approach.
