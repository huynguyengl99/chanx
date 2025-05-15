Introduction
============
What is Chanx?
--------------
Chanx is a comprehensive toolkit for Django Channels that simplifies building real-time WebSocket applications.
It extends Django Channels with crucial features that production applications need, including authentication,
message validation, group management, and testing utilities.

While Django Channels provides the core infrastructure for handling WebSockets in Django, Chanx adds higher-level
abstractions to make development faster, more structured, and less error-prone.

Why use Chanx?
--------------
**Problem: Django Channels is minimal by design**

Django Channels provides a solid foundation for asynchronous applications, but leaves many implementation
details to developers. This leads to:

- Reimplementing authentication and permission handling
- Creating ad-hoc message validation schemes
- Building custom testing infrastructure
- Managing WebSocket connections manually

**Solution: Chanx adds what Channels leaves out**

Chanx fills these gaps with a cohesive framework that provides:

1. **DRF-style Authentication**: Use the same authentication classes you already use in your REST API

.. code-block:: python

  from chanx.generic.websocket import AsyncJsonWebsocketConsumer

  class MyConsumer(AsyncJsonWebsocketConsumer):
      authentication_classes = [TokenAuthentication, SessionAuthentication]
      permission_classes = [IsAuthenticated]

2. **Type-safe Messaging**: Schema validation with Pydantic for incoming and outgoing messages

.. code-block:: python

  from chanx.messages.base import BaseMessage

  class ChatMessage(BaseMessage):
      action: Literal["chat"] = "chat"
      payload: str

3. **Automatic Group Management**: Simplified pub/sub functionality

.. code-block:: python

  async def build_groups(self):
      return [f"room_{self.room_id}"]

  async def receive_message(self, message):
      await self.send_group_message(message)

4. **Enhanced URL Routing**: Django-style routing utilities for WebSocket endpoints with type hints support

.. code-block:: python

  from chanx.routing import path, re_path, include

  router = [
      path('ws/chat/<str:room_id>/', ChatConsumer.as_asgi()),
      path('ws/apps/', include('apps.routing')),
  ]

5. **Testing Utilities**: Specialized tools for WebSocket testing, including multi-user scenarios

.. code-block:: python

  from chanx.testing import WebsocketTestCase

  class TestChat(WebsocketTestCase):
      async def test_chat_message(self):
          await self.auth_communicator.connect()
          await self.auth_communicator.assert_authenticated_status_ok()

          await self.auth_communicator.send_message(ChatMessage(payload="Hello"))
          response = await self.auth_communicator.receive_all_json()
          assert response[0]["payload"] == "Hello"

      async def test_multi_user(self):
          # Create multiple communicators for different users
          second_user_comm = self.create_communicator(headers=second_user_headers)
          await second_user_comm.connect()
          # Test group interactions...

6. **Developer Tooling**: In-browser WebSocket playground for exploring and testing endpoints

7. **Object-level Permissions**: Support for DRF object-level permission checks

.. code-block:: python

  from chanx.generic.websocket import AsyncJsonWebsocketConsumer

  class MyConsumer(AsyncJsonWebsocketConsumer):
      queryset = Room.objects.all()
      permission_classes = [IsRoomMember]

8. **Discriminated Union Messages**: Runtime validation of message types with action discriminator

.. code-block:: python

  from chanx.messages.base import BaseIncomingMessage

  class MyIncomingMessage(BaseIncomingMessage):
      message: PingMessage | ChatMessage | JoinMessage

9. **Full Type Hints Support**: Complete mypy and pyright support for better IDE integration and type safety

Key Benefits
------------
- **Reduced Boilerplate**: Write less code to implement common WebSocket patterns
- **Type Safety**: Catch message structure errors at development time
- **Consistency**: Use the same authentication and permission patterns as your REST API
- **Modularity**: Organize WebSocket routes with an intuitive include system
- **Testability**: Simplified testing with specialized utilities for multi-user scenarios
- **Documentation**: Comprehensive documentation and examples

Architecture Overview
---------------------
Chanx is built around several key components:

- **WebSocket Consumers**: Base consumer classes with integrated authentication and permissions
- **Message System**: Pydantic-based message validation with discriminated unions
- **URL Routing**: Django-style routing utilities for WebSocket endpoints with modular organization
- **Authenticator**: Bridge between WebSocket connections and DRF authentication
- **Testing Framework**: Specialized test case and communicator classes with multi-user support
- **Playground UI**: Visual interface for exploring and testing WebSocket endpoints

Each component is designed to work together while remaining modular enough to be used independently when needed.

Who should use Chanx?
---------------------
Chanx is ideal for:

- Django developers building real-time features
- Projects that already use Django REST Framework
- Applications requiring authenticated WebSocket connections
- Teams that value type safety and validation
- Developers who want to reduce boilerplate code
- Projects using mypy or pyright for type checking

Next Steps
----------
- :doc:`installation` - Install and configure Chanx in your project
- :doc:`quick-start` - Build your first WebSocket endpoint
- :doc:`user-guide/index` - Explore the user guide for detailed information
