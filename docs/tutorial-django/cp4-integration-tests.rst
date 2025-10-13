Part 5: Integration Tests
=========================

In this final part, you'll write comprehensive integration tests for all your WebSocket consumers. You'll learn how to:

- Use Chanx's ``WebsocketTestCase`` for testing WebSocket consumers
- Mock external services (OpenAI API)
- Test with real Celery workers
- Use ``receive_all_messages()`` with stop actions for predictable test assertions
- Configure pytest for Django projects

By the end, you'll have a complete test suite that ensures your WebSocket endpoints work correctly.

Starting Point
--------------

Make sure you've completed Part 4. If you want to start fresh from checkpoint 4:

.. code-block:: bash

   git checkout cp4
   git reset --hard

Step 1: Install Test Dependencies
----------------------------------

Add pytest and pytest-django to your development dependencies:

.. code-block:: bash

   uv add --dev pytest pytest-django

This installs:

- ``pytest`` - Testing framework
- ``pytest-django`` - Django integration for pytest

Step 2: Configure Pytest
-------------------------

**Create** ``chanx_django/pytest.ini``:

.. code-block:: ini

   [pytest]
   DJANGO_SETTINGS_MODULE = config.settings.test

   # Warnings
   filterwarnings =
       ignore::DeprecationWarning

This configures pytest to:

- Use the test settings module
- Filter deprecation warnings

**Create** ``chanx_django/conftest.py``:

.. code-block:: python

   """Pytest configuration and fixtures for chanx_django project."""

   from typing import Any

   import pytest

   pytest_plugins = ("celery.contrib.pytest",)


   @pytest.fixture(scope="session")
   def celery_config() -> dict[str, Any]:
       """Celery configuration for testing."""
       return {
           "broker_url": "memory://",
           "result_backend": "cache+memory://",
           "task_always_eager": False,
           "task_eager_propagates": True,
       }

This sets up Celery for testing:

- ``pytest_plugins`` - Loads Celery's pytest plugin for ``celery_worker`` fixture
- ``celery_config`` - Configures Celery to use in-memory broker/backend for tests
- ``task_always_eager=False`` - Tasks run asynchronously (more realistic)

Step 3: Create Test Settings
-----------------------------

**Create** ``config/settings/test.py``:

.. code-block:: python

   from .base import *  # noqa

   CHANX = {"SEND_COMPLETION": True}

The ``SEND_COMPLETION`` setting enables completion signals after each message/event, which helps tests know when to stop receiving messages.

Step 4: Test Chat Consumer
---------------------------

**Create test directory and files:**

.. code-block:: bash

   mkdir -p chat/tests
   touch chat/tests/__init__.py

**Create** ``chat/tests/test_chat_consumer.py``:

.. code-block:: python

   """Tests for ChatConsumer WebSocket functionality."""

   from typing import cast

   from chanx.channels.testing import WebsocketTestCase
   from chanx.constants import GROUP_ACTION_COMPLETE
   from chanx.messages.incoming import PingMessage
   from chanx.messages.outgoing import PongMessage

   from chat.consumers.chat_consumer import ChatConsumer
   from chat.messages import ChatMessagePayload, NewChatMessage


   class ChatConsumerTestCase(WebsocketTestCase):
       """Unit tests for ChatConsumer - focuses on group chat broadcasting."""

       consumer = ChatConsumer

       def setUp(self) -> None:
           super().setUp()
           self.group_name = "test-room"
           self.ws_path = f"/ws/chat/{self.group_name}/"

       async def test_connect_and_ping(self) -> None:
           """Test basic connection and ping/pong functionality."""
           await self.auth_communicator.connect()
           await self.auth_communicator.send_message(PingMessage())

           messages = await self.auth_communicator.receive_all_messages()
           assert messages == [PongMessage()]

       async def test_broadcast_message_to_group(self) -> None:
           """Test message broadcasting to all group members."""
           # Connect two users to the same group
           await self.auth_communicator.connect()
           communicator2 = self.create_communicator()
           await communicator2.connect()

           # User 1 sends message
           message = NewChatMessage(
               payload=ChatMessagePayload(message="Hello everyone!", name="User1")
           )
           await self.auth_communicator.send_message(message)

           # Only user 2 should receive message
           messages1 = await self.auth_communicator.receive_all_messages(
               stop_action=GROUP_ACTION_COMPLETE, timeout=0.2
           )
           messages2 = await communicator2.receive_all_messages(
               stop_action=GROUP_ACTION_COMPLETE
           )

           assert len(messages1) == 0  # due to exclude_current=True
           assert len(messages2) == 1

           received2 = cast(NewChatMessage, messages2[0])
           assert received2.action == "new_chat_message"
           assert received2.payload.message == "Hello everyone!"
           assert received2.payload.name == "User1"

       async def test_group_isolation(self) -> None:
           """Test that messages are isolated to specific groups."""
           # User 1 in room1
           communicator_room1 = self.create_communicator(ws_path="/ws/chat/room1/")
           await communicator_room1.connect()

           # User 2 in room2
           communicator_room2 = self.create_communicator(ws_path="/ws/chat/room2/")
           await communicator_room2.connect()

           # Send message in room1
           message = NewChatMessage(
               payload=ChatMessagePayload(message="Room1 message", name="User1")
           )
           await communicator_room1.send_message(message)

           # User in room2 should not receive it
           assert await communicator_room2.receive_nothing()

**What we're testing:**

- **test_connect_and_ping**: Basic WebSocket connectivity
- **test_broadcast_message_to_group**: Group broadcasting with ``exclude_current=True``
- **test_group_isolation**: Messages don't leak between different groups

**Test flow (broadcast test):**

1. Connect two users to the same group (``test-room``)
2. User 1 sends a chat message
3. User 1 receives nothing (``exclude_current=True`` in consumer)
4. User 2 receives the broadcasted message

**Critical code:**

.. code-block:: python

   # Create second communicator for multi-user test
   communicator2 = self.create_communicator()

   # Use GROUP_ACTION_COMPLETE for broadcast tests
   messages = await communicator2.receive_all_messages(
       stop_action=GROUP_ACTION_COMPLETE  # Waits for group message
   )

   # Assert no messages received
   assert await communicator_room2.receive_nothing()

Step 5: Test Assistants Consumer
---------------------------------

**Create** ``assistants/tests/__init__.py`` (empty file):

.. code-block:: bash

   mkdir -p assistants/tests
   touch assistants/tests/__init__.py

**Create** ``assistants/tests/test_assistant_consumer.py``:

.. code-block:: python

   """Tests for ConversationAssistantConsumer WebSocket functionality."""

   from typing import cast
   from unittest.mock import Mock, patch

   from chanx.channels.testing import WebsocketTestCase
   from chanx.messages.incoming import PingMessage
   from chanx.messages.outgoing import PongMessage

   from assistants.conversation_consumer import ConversationAssistantConsumer
   from assistants.messages import (
       AssistantMessage,
       CompleteStreamingMessage,
       StreamingMessage,
       StreamingStartMessage,
   )


   class TestConversationAssistantConsumer(WebsocketTestCase):
       """Unit tests for ConversationAssistantConsumer - focuses on AI streaming functionality."""

       consumer = ConversationAssistantConsumer

       def setUp(self) -> None:
           super().setUp()
           self.ws_path = "/ws/assistants/"

       async def test_connect_and_ping(self) -> None:
           """Test basic connection and ping/pong functionality."""
           await self.auth_communicator.connect()
           await self.auth_communicator.send_message(PingMessage())

           messages = await self.auth_communicator.receive_all_messages()
           assert messages == [PongMessage()]

       @patch("assistants.conversation_consumer.OpenAIService")
       async def test_assistant_message_streaming_flow(
           self, mock_openai_service: Mock
       ) -> None:
           """Test complete AI streaming flow: start → chunks → complete."""
           # Mock AI service to return streaming tokens
           mock_service = Mock()
           mock_service.generate_stream.return_value = iter(["Hello", " ", "world"])
           mock_openai_service.return_value = mock_service

           await self.auth_communicator.connect()

           # Send user message
           await self.auth_communicator.send_message(
               AssistantMessage(payload="Test message")
           )

           # Receive all streaming messages
           messages = await self.auth_communicator.receive_all_messages()

           # Verify message sequence: start → streaming chunks → complete
           assert len(messages) >= 3
           assert cast(StreamingStartMessage, messages[0]).action == "streaming_start"
           assert (
               cast(CompleteStreamingMessage, messages[-1]).action == "complete_streaming"
           )

           # Verify streaming chunks
           streaming_chunks = messages[1:-1]
           for chunk in streaming_chunks:
               assert cast(StreamingMessage, chunk).action == "streaming"

           # Verify service was called with user message
           mock_service.generate_stream.assert_called_once()
           call_args = mock_service.generate_stream.call_args
           assert call_args[0][0] == "Test message"
           assert call_args[0][1] == []  # Empty history on first message

       @patch("assistants.conversation_consumer.OpenAIService")
       async def test_conversation_history_maintained(
           self, mock_openai_service: Mock
       ) -> None:
           """Test that conversation history is maintained across messages."""
           mock_service = Mock()
           mock_service.generate_stream.side_effect = [
               iter(["First", " response"]),
               iter(["Second", " response"]),
           ]
           mock_openai_service.return_value = mock_service

           await self.auth_communicator.connect()

           # First message
           await self.auth_communicator.send_message(
               AssistantMessage(payload="First question")
           )
           await self.auth_communicator.receive_all_messages()

           # Second message
           await self.auth_communicator.send_message(
               AssistantMessage(payload="Second question")
           )
           await self.auth_communicator.receive_all_messages()

           # Verify history was maintained
           assert mock_service.generate_stream.call_count == 2
           second_call_history = mock_service.generate_stream.call_args_list[1][0][1]

           assert len(second_call_history) == 2
           assert second_call_history[0] == {"role": "user", "content": "First question"}
           assert second_call_history[1] == {
               "role": "assistant",
               "content": "First response",
           }

**What we're testing:**

- **test_connect_and_ping**: Basic WebSocket connectivity
- **test_assistant_message_streaming_flow**: Streaming sequence (start → chunks → complete) and mock verification
- **test_conversation_history_maintained**: Stateful consumer maintains conversation context across messages

**Test flow (streaming test):**

1. Mock OpenAI service to return 3 tokens: ``["Hello", " ", "world"]``
2. Send user message "Test message"
3. Receive streaming start signal
4. Receive 3 streaming chunks (one per token)
5. Receive streaming complete signal
6. Verify mock was called with correct message and empty history

**Critical code:**

.. code-block:: python

   # Mock OpenAI to return streaming tokens
   @patch("assistants.conversation_consumer.OpenAIService")
   mock_service.generate_stream.return_value = iter(["Hello", " ", "world"])

   # Verify message sequence
   assert messages[0].action == "streaming_start"
   assert messages[-1].action == "complete_streaming"

   # Inspect mock call arguments
   call_args = mock_service.generate_stream.call_args
   assert call_args[0][1] == []  # Empty history on first message

Step 6: Test System Consumer
-----------------------------

**Create** ``system/tests/__init__.py`` (empty file):

.. code-block:: bash

   mkdir -p system/tests
   touch system/tests/__init__.py

**Create** ``system/tests/test_system_consumer.py``:

.. code-block:: python

   """Tests for SystemConsumer WebSocket functionality."""

   from typing import cast

   import pytest
   from celery.apps.worker import Worker
   from chanx.channels.testing import WebsocketTestCase
   from chanx.constants import EVENT_ACTION_COMPLETE
   from chanx.messages.incoming import PingMessage
   from chanx.messages.outgoing import PongMessage

   from system.consumers.system_consumer import SystemConsumer
   from system.messages import (
       JobQueued,
       JobResult,
       SystemMessage,
       TaskPayload,
   )


   class TestSystemConsumer(WebsocketTestCase):
       """Unit tests for SystemConsumer - tests task queueing and event handling."""

       consumer = SystemConsumer

       @pytest.fixture(autouse=True)
       def _inject_fixtures(
           self,
           celery_worker: Worker,
       ) -> None:
           self.celery_worker: Worker = celery_worker

       def setUp(self) -> None:
           super().setUp()
           self.ws_path = "/ws/system/"

       async def test_connect_and_ping(self) -> None:
           """Test basic connection and ping/pong functionality."""
           await self.auth_communicator.connect()
           await self.auth_communicator.send_message(PingMessage())

           messages = await self.auth_communicator.receive_all_messages()
           assert messages == [PongMessage()]

       async def test_queue_task_returns_acknowledgment(self) -> None:
           """Test that queueing a task returns acknowledgment."""
           await self.auth_communicator.connect()

           # Queue task
           message = SystemMessage(
               payload=TaskPayload(task_type="translate", content="hello")
           )
           await self.auth_communicator.send_message(message)

           # Receive acknowledgment
           messages = await self.auth_communicator.receive_all_messages(timeout=1)

           assert len(messages) == 1
           job_queued = cast(JobQueued, messages[0])
           assert job_queued.action == "job_queued"
           assert "Job queued" in job_queued.payload
           assert "translate" in job_queued.payload

       async def test_translate_task_end_to_end(self) -> None:
           """Test full translate task execution with real Celery worker."""
           await self.auth_communicator.connect()

           # Queue translate task
           message = SystemMessage(
               payload=TaskPayload(task_type="translate", content="hello")
           )
           await self.auth_communicator.send_message(message)

           # Receive acknowledgment
           messages = await self.auth_communicator.receive_all_messages()
           assert len(messages) == 1
           assert messages[0].action == "job_queued"

           # Wait for task to complete (2s + buffer)
           result_messages = await self.auth_communicator.receive_all_messages(
               stop_action=EVENT_ACTION_COMPLETE, timeout=4
           )

           # Verify result
           assert len(result_messages) == 1
           job_result = cast(JobResult, result_messages[0])
           assert job_result.action == "job_result"
           assert "Translated" in job_result.payload
           assert "hola" in job_result.payload

**What we're testing:**

- **test_connect_and_ping**: Basic WebSocket connectivity
- **test_queue_task_returns_acknowledgment**: Task queueing returns immediate acknowledgment
- **test_translate_task_end_to_end**: Full flow with real Celery worker processing task and returning result via channel layer

**Test flow (end-to-end test):**

1. Connect to WebSocket
2. Send ``SystemMessage`` with task type "translate" and content "hello"
3. Receive immediate ``JobQueued`` acknowledgment
4. Celery worker processes task (2 seconds)
5. Worker sends ``JobResult`` via ``send_event_sync()`` to channel layer
6. ``@event_handler`` receives event and forwards to WebSocket
7. Client receives ``JobResult`` with translation

**Critical code:**

.. code-block:: python

   # Inject real Celery worker fixture
   @pytest.fixture(autouse=True)
   def _inject_fixtures(self, celery_worker: Worker) -> None:
       self.celery_worker: Worker = celery_worker

   # First receive: immediate acknowledgment
   messages = await self.auth_communicator.receive_all_messages()
   assert messages[0].action == "job_queued"

   # Second receive: wait for event from Celery worker
   result_messages = await self.auth_communicator.receive_all_messages(
       stop_action=EVENT_ACTION_COMPLETE,  # Wait for event completion
       timeout=4  # Task takes 2s + buffer
   )

Step 7: Run Tests
-----------------

**Run all tests:**

.. code-block:: bash

   cd chanx_django
   pytest

**Run specific test file:**

.. code-block:: bash

   pytest chat/tests/test_chat_consumer.py

**Run with verbose output:**

.. code-block:: bash

   pytest -v

**Run specific test:**

.. code-block:: bash

   pytest system/tests/test_system_consumer.py::TestSystemConsumer::test_translate_task_end_to_end

You should see output like:

.. code-block:: text

   ========================= test session starts =========================
   collected 16 items

   assistants/tests/test_assistant_consumer.py .....              [ 31%]
   chat/tests/test_chat_consumer.py .....                         [ 62%]
   system/tests/test_system_consumer.py ......                    [100%]

   ========================= 16 passed in 48.09s =========================

Testing Summary
---------------

**Three consumer types, three test strategies:**

1. **Chat**: Multi-user group broadcasting tests

   - Use ``GROUP_ACTION_COMPLETE`` for broadcasts
   - Create multiple communicators with ``self.create_communicator()``
   - Test group isolation with different ``ws_path``

2. **Assistants**: Mocking external services (OpenAI)

   - Mock with ``@patch("module.Service")``
   - Simulate streaming with ``iter(["token1", "token2"])``
   - Verify message sequence and mock call arguments

3. **System**: Real Celery integration tests

   - Inject ``celery_worker`` fixture for real task execution
   - Use ``EVENT_ACTION_COMPLETE`` for channel layer events
   - Test WebSocket → Celery → WebSocket flow

**Stop actions control when to stop receiving:**

- ``MESSAGE_ACTION_COMPLETE`` - After direct responses (default)
- ``GROUP_ACTION_COMPLETE`` - After group broadcasts
- ``EVENT_ACTION_COMPLETE`` - After channel layer events

What You've Learned
-------------------

Congratulations! You've completed the Chanx Django tutorial. You've built a full-featured real-time application with:

**Part 1: Setup Chanx**

- ✅ Installed and configured Chanx
- ✅ Set up WebSocket routing
- ✅ Enabled AsyncAPI documentation

**Part 2: Chat WebSocket**

- ✅ Created type-safe message models
- ✅ Built WebSocket consumer with ``@ws_handler``
- ✅ Implemented group broadcasting
- ✅ Dynamic URL routing

**Part 3: Assistants WebSocket**

- ✅ Server-initiated streaming messages
- ✅ Stateful consumers with conversation history
- ✅ External API integration (OpenAI)
- ✅ Union types for multiple outputs
- ✅ Enhanced AsyncAPI metadata

**Part 4: System WebSocket**

- ✅ Channel layer events with ``@event_handler``
- ✅ Celery background task integration
- ✅ Server-to-server communication
- ✅ Management commands
- ✅ Generic type parameters for type safety

**Part 5: Integration Tests**

- ✅ Comprehensive integration tests
- ✅ WebSocket testing with ``WebsocketTestCase``
- ✅ Mocking external services
- ✅ Real Celery worker integration
- ✅ Stop actions for predictable assertions

The complete code is available at the ``cp5`` branch:

.. code-block:: bash

   git checkout cp5

Next Steps
----------

Now that you've mastered Chanx fundamentals, explore:

- **User Guide**: Deep dive into advanced features and patterns
- **API Reference**: Complete API documentation
- **Examples**: More real-world examples and use cases
- **AsyncAPI**: Learn to customize your API documentation

Happy building with Chanx! 🚀
