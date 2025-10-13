Part 5: Comprehensive WebSocket Testing
========================================

In this final part, you'll learn how to test WebSocket consumers comprehensively. This demonstrates:

- Setting up pytest for WebSocket testing
- Using Chanx testing utilities
- Testing message flows and broadcasting
- Testing ARQ worker integration
- Testing external messaging

Test Setup
----------

**Create** ``src/pytest.ini`` for pytest configuration:

.. code-block:: ini

   [pytest]
   filterwarnings =
       ignore::DeprecationWarning
   env =
       SEND_COMPLETION=True
   asyncio_default_fixture_loop_scope = function

**Understanding SEND_COMPLETION:**

The ``SEND_COMPLETION=True`` environment variable enables special completion messages that are crucial for testing. When enabled:

- After single message replies complete → sends ``MESSAGE_ACTION_COMPLETE`` message
- After group broadcasts complete → sends ``GROUP_ACTION_COMPLETE`` message
- After event handlers complete → sends ``EVENT_ACTION_COMPLETE`` message

These completion messages tell tests when to stop waiting for messages. Without them, tests will wait until they hit the base timeout, making your test suite slower. With ``stop_action``, tests can finish immediately when the expected message arrives, providing early circuit breaking and faster test execution. Our ``BaseConsumer`` checks this environment variable to enable this behavior during testing.

.. code-block:: python

   # In BaseConsumer
   send_completion = bool(os.environ.get("SEND_COMPLETION", None))

In tests, you use these constants with ``stop_action``:

.. code-block:: python

   from chanx.constants import MESSAGE_ACTION_COMPLETE, GROUP_ACTION_COMPLETE, EVENT_ACTION_COMPLETE

   # Wait for single message reply to complete
   replies = await comm.receive_all_messages(stop_action=MESSAGE_ACTION_COMPLETE)

   # Wait for broadcast to complete
   messages = await comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

   # Wait for event handler to complete
   results = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)

**Create** ``src/conftest.py`` for shared fixtures:

.. code-block:: python

   from typing import Any

   import pytest_asyncio
   from arq import create_pool
   from arq.worker import Worker

   from .tasks import REDIS_SETTINGS, WorkerSettings


   @pytest_asyncio.fixture(scope="function")
   async def bg_worker() -> Any:
       """Create a real ARQ worker for testing."""
       redis = await create_pool(REDIS_SETTINGS)

       worker = Worker(
           functions=WorkerSettings.functions,
           redis_pool=redis,
           burst=True,  # Process jobs immediately and exit
           poll_delay=0.1,  # Fast polling for tests
       )

       yield worker
       await redis.aclose()

**Key points:**

- ``bg_worker`` fixture creates a real ARQ worker for testing
- ``burst=True`` - Worker processes all jobs and exits (perfect for tests)
- ``poll_delay=0.1`` - Fast polling for quicker tests

Testing System Chat Consumer
-----------------------------

**Create** ``src/tests/test_system_chat.py``:

.. code-block:: python

   from typing import cast

   import pytest
   from chanx.fast_channels.testing import WebsocketCommunicator
   from chanx.messages.incoming import PingMessage
   from chanx.messages.outgoing import PongMessage

   from src.apps.system_chat.consumer import SystemMessageConsumer
   from src.apps.system_chat.messages import (
       MessagePayload,
       SystemEchoMessage,
       UserMessage,
   )
   from src.main import app


   @pytest.mark.asyncio
   async def test_system_socket() -> None:
       async with WebsocketCommunicator(
           app, "/ws/system", consumer=SystemMessageConsumer
       ) as comm:
           # Receive connection message
           init_messages = await comm.receive_all_messages(stop_action="system_echo")
           assert len(init_messages) == 1

           init_message = cast(SystemEchoMessage, init_messages[0])
           assert init_message.payload.message == "🔧 System: Connection established!"

           # Test ping-pong
           await comm.send_message(PingMessage())
           replies = await comm.receive_all_messages()
           assert len(replies) == 1
           assert replies == [PongMessage()]

           # Test echo
           test_message = "This is a test message"
           await comm.send_message(
               UserMessage(payload=MessagePayload(message=test_message))
           )
           replies = await comm.receive_all_messages()
           assert len(replies) == 1
           assert replies == [
               SystemEchoMessage(
                   payload=MessagePayload(message=f"🔧 System Echo: {test_message}")
               )
           ]

**Understanding WebsocketCommunicator:**

.. code-block:: python

   async with WebsocketCommunicator(
       app,  # FastAPI app
       "/ws/system",  # WebSocket path
       consumer=SystemMessageConsumer  # Consumer class (optional but recommended)
   ) as comm:

- Context manager handles connection/disconnection
- ``send_message()`` - Send messages to WebSocket
- ``receive_all_messages()`` - Receive messages from WebSocket
- ``stop_action`` - Stop receiving when message with this action arrives

Testing Room Chat Consumer
---------------------------

**Create** ``src/tests/test_room_chat.py``:

.. code-block:: python

   from typing import cast

   import pytest
   from chanx.constants import GROUP_ACTION_COMPLETE
   from chanx.fast_channels.testing import WebsocketCommunicator
   from chanx.messages.incoming import PingMessage
   from chanx.messages.outgoing import PongMessage

   from src.apps.room_chat.consumer import RoomChatConsumer
   from src.apps.room_chat.messages import (
       RoomChatMessage,
       RoomMessagePayload,
       RoomNotificationMessage,
   )
   from src.main import app


   @pytest.mark.asyncio
   async def test_room_chat_ping() -> None:
       room_name = "my-room"
       async with WebsocketCommunicator(
           app, f"/ws/room/{room_name}", consumer=RoomChatConsumer
       ) as comm:
           await comm.send_message(PingMessage())
           replies = await comm.receive_all_messages()
           assert replies == [PongMessage()]


   @pytest.mark.asyncio
   async def test_room_chat_broadcast_messaging() -> None:
       room_name = "my-room"

       # Create two clients in the same room
       first_comm = WebsocketCommunicator(
           app, f"/ws/room/{room_name}", consumer=RoomChatConsumer
       )
       second_comm = WebsocketCommunicator(
           app, f"/ws/room/{room_name}", consumer=RoomChatConsumer
       )

       # Connect first client
       await first_comm.connect()
       assert await first_comm.receive_nothing()

       # Connect second client
       await second_comm.connect()

       # First client should receive join notification
       notified_messages = await first_comm.receive_all_messages(
           stop_action=GROUP_ACTION_COMPLETE
       )
       assert len(notified_messages) == 1
       notified_message = cast(RoomNotificationMessage, notified_messages[0])
       assert notified_message.payload.message == f"🚪 Someone joined room '{room_name}'"

       # Second client doesn't see their own join (exclude_current=True)
       assert await second_comm.receive_nothing()

       # First client sends message
       room_message = "This is a test message"
       expected_message = RoomNotificationMessage(
           payload=RoomMessagePayload(message=f"💬 {room_message}", room_name=room_name)
       )

       await first_comm.send_message(
           RoomChatMessage(payload=RoomMessagePayload(message=room_message))
       )

       # First client receives their own broadcast (exclude_current=False in this consumer)
       first_comm_replies = await first_comm.receive_all_messages(
           stop_action=GROUP_ACTION_COMPLETE
       )
       assert len(first_comm_replies) == 1
       assert first_comm_replies == [expected_message]

       # Second client also receives the message
       second_comm_replies = await second_comm.receive_all_messages(
           stop_action=GROUP_ACTION_COMPLETE
       )
       assert len(second_comm_replies) == 1
       assert second_comm_replies == [expected_message]

       await first_comm.disconnect()
       await second_comm.disconnect()

**Key testing patterns:**

- ``GROUP_ACTION_COMPLETE`` - Special action sent after group broadcasts complete
- ``receive_nothing()`` - Assert no messages received
- Multiple communicators - Test broadcasting between clients
- Manual ``connect()``/``disconnect()`` - Control connection timing

Testing Background Jobs
------------------------

**Create** ``src/tests/test_background_jobs.py``:

.. code-block:: python

   from typing import Any, cast

   import pytest
   from chanx.constants import EVENT_ACTION_COMPLETE
   from chanx.fast_channels.testing import WebsocketCommunicator

   from src.apps.background_jobs.consumer import BackgroundJobConsumer
   from src.apps.background_jobs.messages import (
       JobMessage,
       JobPayload,
       JobStatusMessage,
   )
   from src.main import app


   @pytest.mark.asyncio
   async def test_job_success(bg_worker: Any) -> None:
       """Test successful job queuing and processing."""
       async with WebsocketCommunicator(
           app, "/ws/background_jobs", consumer=BackgroundJobConsumer
       ) as comm:
           # Skip connection message
           await comm.receive_all_messages(stop_action="job_status")

           # Send job message
           message_to_translate = "hello"
           job_message = JobMessage(
               payload=JobPayload(type="translate", content=message_to_translate)
           )
           await comm.send_message(job_message)

           # Receive queuing and queued messages
           replies = await comm.receive_all_messages()
           assert len(replies) == 2

           queuing_msg = cast(JobStatusMessage, replies[0])
           assert queuing_msg.payload["status"] == "queuing"

           queued_msg = cast(JobStatusMessage, replies[1])
           assert queued_msg.payload["status"] == "queued"

           # Process jobs with real ARQ worker
           await bg_worker.async_run()

           # Receive job result
           results = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)
           assert len(results) == 1
           translated_result = cast(JobStatusMessage, results[0])

           translated_text = f"🌍 Translated: '{message_to_translate}' → 'hola'"
           assert translated_result == JobStatusMessage(
               payload={"status": "result", "message": translated_text}
           )

**Key points:**

- ``bg_worker`` fixture - Real ARQ worker for testing
- ``bg_worker.async_run()`` - Process all queued jobs
- ``EVENT_ACTION_COMPLETE`` - Special action sent after event handler completes
- Tests complete flow: queue → process → result

Testing External Messaging
---------------------------

**Create** ``src/tests/test_showcase.py`` (excerpt):

.. code-block:: python

   import pytest
   from chanx.constants import GROUP_ACTION_COMPLETE
   from chanx.fast_channels.testing import WebsocketCommunicator

   from src.apps.showcase.consumer import ChatConsumer
   from src.external_sender import send_chat_message
   from src.main import app


   @pytest.mark.asyncio
   async def test_external_sender_broadcast() -> None:
       """Test external sender script broadcasts to consumers."""
       chat_comm = WebsocketCommunicator(app, "/ws/chat", consumer=ChatConsumer)

       await chat_comm.connect()

       # Clear initial connection messages
       await chat_comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

       # Call external sender function
       await send_chat_message()

       # Receive broadcasted message
       chat_replies = await chat_comm.receive_all_messages(
           stop_action=GROUP_ACTION_COMPLETE
       )
       assert len(chat_replies) == 1
       # Assert message content...

       await chat_comm.disconnect()

This tests that external scripts can successfully send messages to WebSocket clients.

Testing AsyncAPI Schema
------------------------

**Create** ``src/tests/test_asyncapi_schema.py``:

.. code-block:: python

   from fastapi.testclient import TestClient

   from src.main import app

   client = TestClient(app)


   def test_asyncapi_schema_html_doc() -> None:
       response = client.get("/asyncapi")
       assert response.status_code == 200
       assert "AsyncApiStandalone.render" in response.text
       assert "Websocket API documentation generated by Chanx" in response.text


   def test_asyncapi_schema_json() -> None:
       response = client.get("/asyncapi.json")
       assert response.status_code == 200
       data = response.json()

       # Verify structure
       assert "asyncapi" in data
       assert "channels" in data
       assert "operations" in data

Tests that AsyncAPI documentation is generated correctly.

Running Tests
-------------

**Run all tests:**

.. code-block:: bash

   pytest

**Run specific test file:**

.. code-block:: bash

   pytest src/tests/test_system_chat.py

**Run with verbose output:**

.. code-block:: bash

   pytest -v

**Run with coverage:**

.. code-block:: bash

   pytest --cov=src --cov-report=html

**Run specific test:**

.. code-block:: bash

   pytest src/tests/test_background_jobs.py::test_job_success

Key Testing Patterns
---------------------

**Pattern 1: Basic message flow**

.. code-block:: python

   async with WebsocketCommunicator(app, "/ws/path", consumer=Consumer) as comm:
       await comm.send_message(InputMessage(...))
       replies = await comm.receive_all_messages()
       assert replies[0] == ExpectedMessage(...)

**Pattern 2: Broadcasting between clients**

.. code-block:: python

   comm1 = WebsocketCommunicator(app, "/ws/path", consumer=Consumer)
   comm2 = WebsocketCommunicator(app, "/ws/path", consumer=Consumer)

   await comm1.connect()
   await comm2.connect()

   await comm1.send_message(Message(...))

   replies1 = await comm1.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)
   replies2 = await comm2.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

   await comm1.disconnect()
   await comm2.disconnect()

**Pattern 3: Testing with ARQ worker**

.. code-block:: python

   async def test_with_worker(bg_worker: Any) -> None:
       async with WebsocketCommunicator(...) as comm:
           await comm.send_message(JobMessage(...))
           await comm.receive_all_messages()  # Skip queuing messages

           await bg_worker.async_run()  # Process jobs

           results = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)
           assert results[0] == ExpectedResult(...)

**Pattern 4: Testing server-initiated messages**

.. code-block:: python

   async with WebsocketCommunicator(...) as comm:
       # Receive connection message (server-initiated)
       init_messages = await comm.receive_all_messages(stop_action="some_action")
       assert init_messages[0] == WelcomeMessage(...)

**Pattern 5: Testing external messaging**

.. code-block:: python

   async with WebsocketCommunicator(...) as comm:
       await comm.connect()
       await comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

       # Call external function
       await some_external_function()

       # Receive broadcasted message
       messages = await comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

Common Assertions
-----------------

**Assert message count:**

.. code-block:: python

   replies = await comm.receive_all_messages()
   assert len(replies) == 2

**Assert message content:**

.. code-block:: python

   assert replies[0] == ExpectedMessage(payload=...)
   assert replies[0].payload.field == "expected_value"

**Assert no messages:**

.. code-block:: python

   assert await comm.receive_nothing()

**Assert message type:**

.. code-block:: python

   from typing import cast
   message = cast(ExpectedMessageType, replies[0])
   assert message.action == "expected_action"

Troubleshooting
---------------

**Test hangs waiting for messages:**

- Check if you're using the correct ``stop_action``
- Verify the consumer actually sends messages
- Use timeout: ``await comm.receive_all_messages(timeout=1.0)``

**ARQ tests fail:**

- Ensure Redis is running: ``docker compose up -d``
- Check ARQ worker fixture is being used
- Verify task functions are registered in ``WorkerSettings``

**Connection messages interfere:**

- Use ``stop_action`` to skip them
- Or call ``receive_all_messages()`` to clear them before testing

**Type checking issues:**

- Use ``cast()`` for proper type hints
- Import message types correctly

Conclusion
----------

Congratulations! You've completed the entire Chanx FastAPI tutorial. You've learned:

**Core Concepts:**

- ✅ Type-safe WebSocket consumers with Pydantic
- ✅ Automatic message routing with ``@ws_handler``
- ✅ Event handlers for server-to-server communication
- ✅ Direct WebSocket and channel layer communication

**Advanced Features:**

- ✅ Dynamic URL routing with path parameters
- ✅ Channel layers with Redis (Pub/Sub and Queue)
- ✅ Background job processing with ARQ
- ✅ External messaging from scripts/endpoints
- ✅ Multi-layer architecture

**Testing:**

- ✅ Comprehensive WebSocket testing with pytest
- ✅ Testing broadcasting and group messaging
- ✅ Testing ARQ worker integration
- ✅ Testing external messaging

You now have the knowledge to build production-ready WebSocket applications with FastAPI and Chanx!

**Next Steps:**

- Build your own WebSocket application
- Explore the :doc:`../reference/fast-channels` for advanced features
- Check out :doc:`../examples/fastapi` for more examples
- Try the :doc:`../tutorial-django/prerequisites` if you're interested in Django

Thank you for completing this FastAPI tutorial! Happy building with Chanx! 🚀
