Introduction
============
What is Chanx?
--------------
Chanx is a comprehensive toolkit for building real-time WebSocket applications across Django Channels, FastAPI,
and any ASGI-compatible framework. It eliminates the complexity of manual message routing, provides automatic
AsyncAPI documentation generation, and offers decorator-based handlers that make WebSocket development as
straightforward as building REST APIs.

Chanx transforms WebSocket development by replacing verbose if/else message routing with clean decorators,
automatically generating type-safe message handling, and providing seamless event broadcasting across your
entire application stack.

Why use Chanx?
--------------
**Problem: WebSocket development is tedious and error-prone**

Building WebSocket applications traditionally requires writing verbose message routing code, manually handling
validation, and maintaining separate documentation. This leads to:

- Massive if/else or switch statements for message routing
- Boilerplate authentication and permission handling across frameworks
- Manual message validation with inconsistent error handling
- No automatic documentation generation
- Complex event broadcasting between different parts of your application

**Solution: Chanx provides decorator-based automation**

Chanx eliminates these pain points with a unified framework that provides:

1. **No More If/Else Hell**: Decorator-based automatic message routing eliminates verbose switch statements

.. code-block:: python

  # Before: Manual routing nightmare
  async def receive_json(self, content):
      action = content.get("action")
      if action == "chat":
          await self.handle_chat(content)
      elif action == "ping":
          await self.handle_ping(content)
      elif action == "join_room":
          await self.handle_join_room(content)
      # ... dozens more elif statements

  # After: Clean decorator-based routing
  from chanx.core.decorators import ws_handler, channel

  @channel(name="chat", description="Real-time chat")
  class ChatConsumer(AsyncJsonWebsocketConsumer):
      @ws_handler(summary="Handle chat messages")
      async def handle_chat(self, message: ChatMessage) -> None:
          await self.broadcast_message(...)

      @ws_handler(summary="Handle ping requests")
      async def handle_ping(self, message: PingMessage) -> PongMessage:
          return PongMessage()

2. **Automatic AsyncAPI Documentation**: Generate comprehensive API docs from your decorated handlers

.. code-block:: python

  # Your decorators automatically generate AsyncAPI 3.0 specs
  @ws_handler(
      summary="Send chat message",
      description="Broadcast message to all room members",
      tags=["chat", "messaging"]
  )
  async def handle_chat(self, message: ChatMessage) -> None:
      # Implementation generates documentation automatically

.. image:: _static/asyncapi-info.png
   :alt: AsyncAPI Documentation automatically generated from Chanx decorators
   :align: center

3. **Send Events from Anywhere**: Seamlessly broadcast events from HTTP views, background tasks, or management scripts

.. code-block:: python

  # From a Django view
  def create_post(request):
      post = Post.objects.create(...)
      # Instantly notify WebSocket clients
      ChatConsumer.broadcast_event_sync(
          NewPostEvent(payload={"title": post.title}),
          groups=["feed_updates"]
      )
      return JsonResponse({"status": "created"})

  # From a Celery task
  @celery.task
  def process_payment(payment_id):
      payment = process_payment_logic(payment_id)
      # Notify user's WebSocket connection
      PaymentConsumer.send_event_sync(
          PaymentCompleteEvent(payload=payment.to_dict()),
          channel_name=f"user_{payment.user_id}"
      )

4. **Multi-Framework Support**: Automatic framework detection with consistent API across Django Channels, FastAPI, and any ASGI framework

.. code-block:: python

  # Same import works everywhere - auto-detects framework
  from chanx.core.websocket import AsyncJsonWebsocketConsumer

  # Framework detection via environment variables:
  # - Django: DJANGO_SETTINGS_MODULE detected automatically
  # - Other frameworks: Set CHANX_USE_DJANGO=false or leave unset

5. **Type-Safe Messaging**: Automatic Pydantic validation with discriminated unions and full IDE support

.. code-block:: python

  from chanx.messages.base import BaseMessage
  from typing import Literal

  class ChatMessage(BaseMessage):
      action: Literal["chat"] = "chat"
      payload: ChatPayload

  class PingMessage(BaseMessage):
      action: Literal["ping"] = "ping"
      payload: None = None

  # Framework automatically builds discriminated unions and routing
  @channel(name="chat")
  class ChatConsumer(AsyncJsonWebsocketConsumer):
      # No manual routing needed - decorators handle everything!

6. **Enhanced Testing**: Framework-specific testing with improved message handling

.. code-block:: python

  # FastAPI and other ASGI frameworks
  from chanx.testing import WebsocketCommunicator

  @pytest.mark.asyncio
  async def test_streaming_response():
      async with WebsocketCommunicator(app, "/ws/chat", consumer=ChatConsumer) as comm:
          await comm.send_message(ChatMessage(payload="Hello"))

          # receive_all_messages waits for stop_action - faster & more reliable
          messages = await comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

          assert messages[0].action == "chat_notification"

  # Django Channels (enhanced)
  from chanx.channels.testing import WebsocketTestCase

  class TestChat(WebsocketTestCase):
      consumer = ChatConsumer

      async def test_event_handling(self):
          await self.auth_communicator.connect()

          # Send events from anywhere in your application
          await ChatConsumer.broadcast_event(
              StreamingEvent(payload=streaming_data),
              [f"user_{self.user.pk}_chat"]
          )

          # Enhanced receive with stop_action handling
          messages = await self.auth_communicator.receive_all_messages(
              stop_action=EVENT_ACTION_COMPLETE
          )

Key Benefits
------------
- **Eliminate If/Else Hell**: Decorator-based routing replaces verbose manual message handling
- **Automatic Documentation**: AsyncAPI 3.0 specs generated directly from your code
- **Event Broadcasting Made Easy**: Send events from anywhere in your application stack
- **Multi-Framework Consistency**: Same API works across Django, FastAPI, and ASGI frameworks
- **Type Safety**: Full mypy/pyright support with automatic discriminated unions
- **Zero Configuration Routing**: Message types automatically routed to the correct handlers
- **Production Ready**: Battle-tested patterns with comprehensive error handling

Architecture Overview
---------------------
Chanx is built around decorator-driven automation:

- **Decorator System**: ``@ws_handler``, ``@event_handler``, and ``@channel`` decorators for automatic routing
- **Message Registry**: Centralized type discovery and discriminated union generation
- **AsyncAPI Generator**: Automatic OpenAPI-style documentation from decorated handlers
- **Multi-Framework Adapters**: Unified API across Django Channels, FastAPI, and ASGI frameworks
- **Event Broadcasting**: Type-safe event sending from HTTP views, tasks, scripts, and consumers
- **Authentication Integration**: Framework-specific authenticators (DRF for Django, custom for others)
- **Enhanced Testing Framework**: Improved Django Channels testing with faster, more reliable message handling via `receive_all_message` with stop actions

The architecture eliminates manual configuration by automatically discovering message types, building routing tables, and generating documentation from your decorated methods.

Who should use Chanx?
---------------------
Chanx is ideal for:

- **Python developers** building real-time features across any ASGI framework
- **Django teams** who want to eliminate WebSocket boilerplate and maintain REST API consistency
- **FastAPI projects** needing robust WebSocket capabilities with automatic documentation
- **Full-stack applications** requiring seamless event broadcasting between HTTP and WebSocket layers
- **Type-safety advocates** who want comprehensive mypy/pyright support for WebSocket development
- **API-first teams** who need automatic AsyncAPI documentation generation
- **DevOps-friendly projects** seeking consistent patterns across multiple Python web frameworks

Next Steps
----------
- :doc:`installation` - Install and configure Chanx in your project
- :doc:`quick-start-django` - Build your first Django WebSocket endpoint
- :doc:`quick-start-fastapi` - Build your first FastAPI WebSocket endpoint
- :doc:`user-guide/prerequisites` - Start with the user guide prerequisites
