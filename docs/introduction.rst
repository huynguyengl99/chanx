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

      class MyConsumer(AsyncJsonWebsocketConsumer):
          authentication_classes = [TokenAuthentication, SessionAuthentication]
          permission_classes = [IsAuthenticated]

2. **Type-safe Messaging**: Schema validation with Pydantic for incoming and outgoing messages

   .. code-block:: python

      class ChatMessage(BaseMessage):
          action: Literal["chat"] = "chat"
          payload: str

3. **Automatic Group Management**: Simplified pub/sub functionality

   .. code-block:: python

      async def build_groups(self):
          return [f"room_{self.room_id}"]

      async def receive_message(self, message):
          await self.send_group_message(message)

4. **Testing Utilities**: Specialized tools for WebSocket testing

   .. code-block:: python

      class TestChat(WebsocketTestCase):
          async def test_chat_message(self):
              await communicator.send_message(ChatMessage(payload="Hello"))
              response = await communicator.receive_all_json()
              assert response[0]["payload"] == "Hello"

5. **Developer Tooling**: In-browser WebSocket playground for exploring and testing endpoints

Key Benefits
------------
- **Reduced Boilerplate**: Write less code to implement common WebSocket patterns
- **Type Safety**: Catch message structure errors at development time
- **Consistency**: Use the same authentication and permission patterns as your REST API
- **Testability**: Simplified testing with specialized utilities
- **Documentation**: Comprehensive documentation and examples

Architecture Overview
---------------------
Chanx is built around several key components:

- **WebSocket Consumers**: Base consumer classes with integrated authentication
- **Message System**: Pydantic-based message validation with discriminated unions
- **Authenticator**: Bridge between WebSocket connections and DRF authentication
- **Testing Framework**: Specialized test case and communicator classes
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

Next Steps
----------
- :doc:`installation` - Install and configure Chanx in your project
- :doc:`quick-start` - Build your first WebSocket endpoint
- :doc:`user-guide/index` - Explore the user guide for detailed information
