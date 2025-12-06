Testing WebSocket Consumers
===========================

Chanx provides enhanced testing utilities that make WebSocket testing reliable and straightforward. The testing framework includes completion signal handling, automatic message collection, and framework-specific authentication support.

Testing Configuration
---------------------

**Django Test Settings:**

.. code-block:: python

    # settings/test.py
    CHANX = {
        'SEND_COMPLETION': True,  # Important for receive_all_messages() to work
        'LOG_WEBSOCKET_MESSAGE': False,  # Reduce test noise
        'LOG_IGNORED_ACTIONS': [],
    }

**FastAPI/Other Frameworks:**

.. code-block:: python

    # Configure via base consumer or environment
    from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer

    class TestBaseConsumer(AsyncJsonWebsocketConsumer):
        send_completion = True  # Enable completion signals for testing
        log_websocket_message = False  # Reduce test noise

Framework-Specific Testing
--------------------------

**FastAPI and ASGI Frameworks:**

- Use ``WebsocketCommunicator`` from ``chanx.fast_channels.testing``
- Async context manager support for automatic cleanup
- Direct pytest integration

**Django Channels:**

- Use ``WebsocketTestCase`` from ``chanx.channels.testing``
- Enhanced Django test case with authentication support
- Automatic ASGI application discovery

FastAPI Testing Examples
------------------------

**Key Benefits of WebsocketCommunicator:**

- **Automatic connection management**: Use **async with** for auto-connect and auto-disconnect
- **No manual cleanup required**: Context manager handles all connection lifecycle
- **Built-in message collection**: Easily gather and assert on received messages

**Basic Test Setup:**

.. code-block:: python

    import pytest
    from chanx.fast_channels.testing import WebsocketCommunicator
    from chanx.constants import GROUP_ACTION_COMPLETE
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    from myapp.main import app
    from myapp.consumers import ChatConsumer

    @pytest.mark.asyncio
    async def test_ping_pong():
        # Context manager automatically connects and disconnects WebSocket
        async with WebsocketCommunicator(
            app, "/ws/chat", consumer=ChatConsumer
        ) as comm:
            # WebSocket is now connected and ready
            await comm.send_message(PingMessage())
            messages = await comm.receive_all_messages()
            # WebSocket automatically disconnected when exiting context
            assert len(messages) == 1
            assert isinstance(messages[0], PongMessage)

**Testing Message Broadcasting:**

.. code-block:: python

    @pytest.mark.asyncio
    async def test_chat_broadcasting():
        # Note: consumer parameter is required for completion signals
        async with WebsocketCommunicator(
            app, "/ws/room/test", consumer=RoomChatConsumer
        ) as first_comm, WebsocketCommunicator(
            app, "/ws/room/test", consumer=RoomChatConsumer
        ) as second_comm:
            # Send a message that triggers broadcasting
            await first_comm.send_message(ChatMessage(payload={"message": "Hello"}))

            # Use GROUP_ACTION_COMPLETE for broadcast scenarios
            first_replies = await first_comm.receive_all_messages(
                stop_action=GROUP_ACTION_COMPLETE
            )
            second_replies = await second_comm.receive_all_messages(
                stop_action=GROUP_ACTION_COMPLETE
            )

            assert len(first_replies) == 1
            assert len(second_replies) == 1

Django Testing Examples
-----------------------

**Basic Test Setup:**

.. code-block:: python

    from chanx.channels.testing import WebsocketTestCase
    from chanx.constants import EVENT_ACTION_COMPLETE

    class TestChatConsumer(WebsocketTestCase):
        consumer = ChatConsumer

        def setUp(self):
            super().setUp()
            self.ws_path = "/ws/chat/"

        def get_ws_headers(self):
            self.user, headers = self.create_user_and_ws_headers()
            return headers

        async def test_authenticated_chat(self):
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            await self.auth_communicator.send_message(
                ChatMessage(payload={"message": "Hello"})
            )

            messages = await self.auth_communicator.receive_all_messages()
            assert len(messages) >= 1

**Multi-User Testing:**

.. code-block:: python

    async def test_multi_user_chat(self):
        # First user
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Second user
        second_user, second_headers = await self.acreate_user_and_ws_headers()
        second_comm = self.create_communicator(headers=second_headers)
        await second_comm.connect()
        await second_comm.assert_authenticated_status_ok()

        # Test interaction between users

Key Testing Methods
-------------------

**WebsocketCommunicator (FastAPI/ASGI):**

.. code-block:: python

    # Context manager (recommended) - auto-connects and auto-disconnects
    async with WebsocketCommunicator(app, "/ws/chat", consumer=ChatConsumer) as comm:
        # Connection established automatically here
        await comm.send_message(PingMessage())
        messages = await comm.receive_all_messages()
        # Connection closed automatically when exiting context

    # Manual connection management (if needed)
    comm = WebsocketCommunicator(app, "/ws/chat", consumer=ChatConsumer)
    await comm.connect()
    # ... do work ...
    await comm.disconnect()

    # Message collection with completion signals
    messages = await comm.receive_all_messages(
        stop_action=GROUP_ACTION_COMPLETE,
        timeout=2.0
    )

**Additional Testing Methods:**

.. code-block:: python

    # Raw JSON methods (for low-level testing)
    await comm.send_json({"action": "custom", "payload": {"data": "test"}})
    json_response = await comm.receive_json(timeout=1.0)

    # Receive exactly one message
    single_message = await comm.receive_message(timeout=1.0)

    # Verify no messages are sent (useful for negative testing)
    await comm.receive_nothing(timeout=0.5)

    # Receive all JSON (without message parsing)
    all_json = await comm.receive_all_json(timeout=2.0)

    # Receive all messages with different completion actions
    messages = await comm.receive_all_messages(stop_action="complete")        # Default
    messages = await comm.receive_all_messages(stop_action="group_complete")  # For broadcasts
    messages = await comm.receive_all_messages(stop_action="event_complete")  # For events
    messages = await comm.receive_all_messages(stop_action="custom_action")   # Any custom action

**Capturing Broadcast Events:**

.. code-block:: python

    from chanx.core.testing import capture_broadcast_events

    # Capture and suppress broadcasts (default: suppress=True)
    with capture_broadcast_events(ChatConsumer) as captured:
        await ChatConsumer.broadcast_event(
            NotificationEvent(payload={"message": "Test"}),
            groups=["users"]
        )
        # Event is captured but not actually broadcast

    # Capture without suppressing (suppress=False)
    with capture_broadcast_events(ChatConsumer, suppress=False) as captured:
        await ChatConsumer.broadcast_event(
            NotificationEvent(payload={"message": "Test"}),
            groups=["users"]
        )
        # Event is both captured AND broadcast

    # Inspect captured events
    assert len(captured) == 1
    assert captured[0]["event"].action == "notification"
    assert captured[0]["groups"] == ["users"]

**WebsocketTestCase (Django):**

.. code-block:: python

    # Primary authenticated communicator
    await self.auth_communicator.connect()
    await self.auth_communicator.assert_authenticated_status_ok()

    # Create additional communicators
    second_comm = self.create_communicator(headers=different_headers)

    # Event broadcasting tests
    await ChatConsumer.broadcast_event(
        NotificationEvent(payload={"message": "test"}),
        groups=[f"user_{self.user.id}"]
    )

Understanding Completion Actions
---------------------------------

Completion actions determine when ``receive_all_messages()`` stops collecting messages:

.. code-block:: python

    from chanx.constants import (
        MESSAGE_ACTION_COMPLETE,   # "complete"
        GROUP_ACTION_COMPLETE,     # "group_complete"
        EVENT_ACTION_COMPLETE,     # "event_complete"
    )

**When to use each completion action:**

- **MESSAGE_ACTION_COMPLETE** (default): For simple request-response patterns with ``@ws_handler``
- **GROUP_ACTION_COMPLETE**: When testing message broadcasting to groups
- **EVENT_ACTION_COMPLETE**: When testing ``send_event()`` or ``broadcast_event()`` calls
- **Custom action strings**: Any custom message action can be used as a stop condition

**Examples:**

.. code-block:: python

    # Testing simple echo (ws_handler that returns directly)
    await comm.send_message(EchoMessage(payload={"text": "hello"}))
    responses = await comm.receive_all_messages()  # Uses MESSAGE_ACTION_COMPLETE

    # Testing broadcast functionality
    await comm.send_message(ChatMessage(payload={"text": "hello everyone"}))
    responses = await comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

    # Testing event broadcasting from outside WebSocket
    await ChatConsumer.broadcast_event(NotificationEvent(...), groups=["users"])
    responses = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)

    # Using custom action as stop condition
    await comm.send_message(StartProcessMessage())
    responses = await comm.receive_all_messages(stop_action="process_complete")  # Custom action

    # Wait for specific status message
    responses = await comm.receive_all_messages(stop_action="job_status")

**Important**: The consumer must be specified for completion signals to work:

.. code-block:: python

    # ✅ Correct - consumer specified
    async with WebsocketCommunicator(app, "/ws/chat", consumer=ChatConsumer) as comm:
        messages = await comm.receive_all_messages(stop_action=GROUP_ACTION_COMPLETE)

    # ❌ Incorrect - no consumer specified
    async with WebsocketCommunicator(app, "/ws/chat") as comm:
        # Completion signals won't work properly

Common Testing Patterns
-----------------------

**Connection Lifecycle:**

.. code-block:: python

    async def test_connection_lifecycle(self):
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Use connection
        await self.auth_communicator.send_message(TestMessage())
        messages = await self.auth_communicator.receive_all_messages()

        # Cleanup handled automatically

**Event Broadcasting:**

.. code-block:: python

    async def test_event_broadcasting(self):
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send event from outside WebSocket (HTTP view, task, etc.)
        await ChatConsumer.broadcast_event(
            NotificationEvent(payload={"message": "System notification"}),
            groups=[f"user_{self.user.id}"]
        )

        messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )
        assert len(messages) == 1

**Capturing Broadcast Events:**

The ``capture_broadcast_events`` utility allows you to capture and inspect broadcast events without needing a WebSocket connection. Similar to ``structlog``'s ``capture_logs()``, this is useful for testing event broadcasting logic in isolation.

.. code-block:: python

    from chanx.core.testing import capture_broadcast_events

    async def test_notification_broadcast(self):
        # Capture broadcast events (default: suppress=True, no actual broadcast)
        with capture_broadcast_events(ChatConsumer) as captured:
            await ChatConsumer.broadcast_event(
                NotificationEvent(payload={"message": "Test notification"}),
                groups=["users"]
            )

        # Assert on captured events
        assert len(captured) == 1
        assert captured[0]["event"].action == "notification"
        assert captured[0]["event"].payload.message == "Test notification"
        assert captured[0]["groups"] == ["users"]

    async def test_multiple_broadcasts(self):
        with capture_broadcast_events(ChatConsumer) as captured:
            # Send multiple events
            await ChatConsumer.broadcast_event(
                NotificationEvent(payload={"message": "First"}),
                groups=["group1", "group2"]
            )
            await ChatConsumer.broadcast_event(
                NotificationEvent(payload={"message": "Second"}),
                groups="single_group"
            )

        # Filter and assert on specific events
        assert len(captured) == 2
        assert captured[0]["groups"] == ["group1", "group2"]
        assert captured[1]["groups"] == "single_group"

        # Filter events by action
        notifications = [e for e in captured if e["event"].action == "notification"]
        assert len(notifications) == 2

    async def test_capture_without_suppressing(self):
        # Set suppress=False to capture AND actually broadcast events
        with capture_broadcast_events(ChatConsumer, suppress=False) as captured:
            await ChatConsumer.broadcast_event(
                NotificationEvent(payload={"message": "Broadcast and capture"}),
                groups=["users"]
            )
            # Events are both captured and sent to channel layer

        assert len(captured) == 1

**Testing Negative Scenarios:**

.. code-block:: python

    async def test_no_unauthorized_messages(self):
        # Connect without authentication
        await self.communicator.connect()

        # Send a message that should be rejected
        await self.communicator.send_message(ProtectedMessage())

        # Verify no response is sent (should timeout)
        await self.communicator.receive_nothing(timeout=0.5)

    async def test_invalid_message_ignored(self):
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send invalid JSON
        await self.auth_communicator.send_json({"invalid": "format"})

        # Should receive no messages back
        await self.auth_communicator.receive_nothing(timeout=0.5)

**Streaming Messages:**

.. code-block:: python

    @pytest.mark.asyncio
    async def test_streaming_response():
        async with WebsocketCommunicator(app, "/ws/ai-chat", consumer=AIConsumer) as comm:
            await comm.send_message(GenerateStoryMessage(payload={"prompt": "Tell me a story"}))

            messages = await comm.receive_all_messages(
                stop_action=EVENT_ACTION_COMPLETE,
                timeout=5.0  # Longer timeout for AI responses
            )

            streaming_messages = [m for m in messages if m.action == "streaming"]
            assert len(streaming_messages) >= 1

Testing Best Practices
----------------------

**1. Use completion signals:**

.. code-block:: python

    # Always use receive_all_messages() with appropriate stop_action
    messages = await comm.receive_all_messages(
        stop_action=GROUP_ACTION_COMPLETE
    )

**2. Handle async properly:**

.. code-block:: python

    # FastAPI: Mark tests as async
    @pytest.mark.asyncio
    async def test_something(): ...

    # Django: Test methods are automatically async in WebsocketTestCase
    async def test_something(self): ...

**3. Clean up connections:**

.. code-block:: python

    # FastAPI: Use context managers (automatic connect/disconnect)
    async with WebsocketCommunicator(...) as comm:
        # WebSocket connects automatically when entering context
        # WebSocket disconnects automatically when exiting context
        pass

    # Django: WebsocketTestCase handles cleanup automatically

**4. Test both success and failure scenarios:**

.. code-block:: python

    # Test successful authentication
    await comm.assert_authenticated_status_ok()

    # Test failed authentication
    auth_msg = await comm.wait_for_auth()
    assert auth_msg.payload.status_code == 403

Next Steps
----------

With comprehensive testing utilities, you can ensure your WebSocket consumers work correctly across all scenarios. Continue to :doc:`framework-integration` for Django views and FastAPI API endpoints that complement your WebSocket consumers.

The enhanced testing framework makes WebSocket testing as reliable as HTTP testing, with automatic cleanup, completion signals, and framework-specific authentication support.
