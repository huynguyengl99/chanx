Testing
=======
Chanx provides specialized testing utilities that make it easier to write comprehensive tests for WebSocket consumers. These tools handle connection management, authentication, message exchange, and test cleanup.

Testing Overview
----------------
Testing WebSocket consumers differs from testing regular HTTP views:

1. Connections are long-lived instead of request/response
2. Authentication happens once at connection time
3. Multiple messages can be exchanged over a single connection
4. Asynchronous code requires special testing approaches

Chanx addresses these challenges with the WebsocketTestCase class and enhanced WebsocketCommunicator.

WebsocketTestCase
-----------------
The `WebsocketTestCase` class extends Django's `TransactionTestCase` with WebSocket-specific functionality:

.. code-block:: python

    from chanx.testing import WebsocketTestCase

    class TestMyConsumer(WebsocketTestCase):
        # Path to test (required)
        ws_path = "/ws/myendpoint/"

        async def test_connect(self):
            # Create a communicator (automatically tracked for cleanup)
            communicator = self.create_communicator()

            # Connect and check result
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

Key features of `WebsocketTestCase`:

1. **Automatic Router Discovery**: Finds your WebSocket application from ASGI configuration
2. **Connection Tracking**: Manages test communicators to ensure proper cleanup
3. **Helper Methods**: Provides utilities for common testing tasks
4. **Authentication Support**: Simplifies testing authenticated connections

Authentication in Tests
-----------------------
To test authenticated WebSocket consumers:

.. code-block:: python

    class TestAuthenticatedConsumer(WebsocketTestCase):
        ws_path = "/ws/secure/"

        def setUp(self):
            super().setUp()
            # Create test user
            self.user = User.objects.create_user(
                username="testuser",
                password="password"
            )

            # Log in with the Django test client
            self.client.login(username="testuser", password="password")

        def get_ws_headers(self):
            """Provide session cookie for WebSocket authentication."""
            cookies = self.client.cookies
            return [
                (b"cookie", f"sessionid={cookies['sessionid'].value}".encode()),
            ]

        async def test_authenticated_connection(self):
            communicator = self.create_communicator()
            connected, _ = await communicator.connect()

            # Assert connection was successful
            self.assertTrue(connected)

            # Verify authentication succeeded
            await communicator.assert_authenticated_status_ok()

Enhanced WebsocketCommunicator
------------------------------
Chanx extends the standard Channels WebsocketCommunicator with additional features:

.. code-block:: python

    from chanx.testing import WebsocketCommunicator

    # Create communicator (normally done by WebsocketTestCase)
    communicator = WebsocketCommunicator(application, "/ws/myendpoint/")

    # Connect with timeout
    connected, _ = await communicator.connect(timeout=3)

    # Handle authentication message
    auth_message = await communicator.wait_for_auth()

    # Send message objects directly
    from myapp.messages import ChatMessage
    await communicator.send_message(ChatMessage(payload="Hello"))

    # Receive all messages until completion
    messages = await communicator.receive_all_json()

    # Assert authentication status
    await communicator.assert_authenticated_status_ok()

    # Check connection closed properly
    await communicator.assert_closed()

Testing Message Exchange
------------------------
To test sending and receiving messages:

.. code-block:: python

    from myapp.messages import PingMessage, ChatMessage

    class TestChatConsumer(WebsocketTestCase):
        ws_path = "/ws/chat/room1/"

        async def test_ping_pong(self):
            communicator = self.create_communicator()
            connected, _ = await communicator.connect()

            # Wait for any authentication messages
            await communicator.wait_for_auth()

            # Send ping message
            await communicator.send_message(PingMessage())

            # Receive all messages until completion
            responses = await communicator.receive_all_json()

            # Check for pong response
            self.assertEqual(responses[0]["action"], "pong")

        async def test_chat_message(self):
            communicator = self.create_communicator()
            await communicator.connect()
            await communicator.wait_for_auth()

            # Send chat message
            await communicator.send_message(ChatMessage(payload="Test message"))

            # Get responses up to completion marker
            responses = await communicator.receive_all_json()

            # Verify the response
            self.assertEqual(len(responses), 1)
            self.assertEqual(responses[0]["action"], "chat")
            self.assertEqual(responses[0]["payload"], "Test message")

Testing Group Messages
----------------------
For testing group messages, you'll need multiple communicators:

.. code-block:: python

    async def test_group_messaging(self):
        # Create two communicators for the same room
        com1 = self.create_communicator(ws_path="/ws/chat/room1/")
        com2 = self.create_communicator(ws_path="/ws/chat/room1/")

        # Connect both
        await com1.connect()
        await com2.connect()

        # Handle authentication
        await com1.wait_for_auth()
        await com2.wait_for_auth()

        # Send message from first client
        await com1.send_message(ChatMessage(payload="Hello from com1"))

        # Check that second client received it
        responses = await com2.receive_all_json(wait_group=True)

        # Verify the message
        self.assertEqual(responses[0]["action"], "chat")
        self.assertEqual(responses[0]["payload"], "Hello from com1")
        self.assertFalse(responses[0]["is_mine"])  # Not sent by com2

        # Disconnect both
        await com1.disconnect()
        await com2.disconnect()

Testing Error Handling
----------------------
Always test error scenarios as well:

.. code-block:: python

    async def test_invalid_message(self):
        communicator = self.create_communicator()
        connected, _ = await communicator.connect()

        # Wait for authentication
        await communicator.wait_for_auth()

        # Send invalid message (missing required fields)
        await communicator.send_json_to({"action": "chat"})  # Missing payload

        # Get error response
        responses = await communicator.receive_all_json()

        # Verify error response
        self.assertEqual(responses[0]["action"], "error")
        self.assertIn("payload", str(responses[0]["payload"]))

Testing Disconnection
---------------------
Test disconnection scenarios to ensure proper cleanup:

.. code-block:: python

    async def test_disconnect_handling(self):
        communicator = self.create_communicator()
        connected, _ = await communicator.connect()

        # Perform actions...

        # Then disconnect
        await communicator.disconnect()

        # After disconnection, can check database state
        # to verify any cleanup operations happened

Testing Permissions
-------------------
Test permission checks for both success and failure:

.. code-block:: python

    async def test_permission_denied(self):
        # Create a user who is not a member of the room
        non_member = User.objects.create_user(
            username="nonmember",
            password="password"
        )

        # Login with this user
        self.client.logout()
        self.client.login(username="nonmember", password="password")

        # Try to connect
        communicator = self.create_communicator()
        connected, code = await communicator.connect()

        # Should be connected initially but disconnected after auth
        self.assertTrue(connected)

        # Wait for auth message
        auth_message = await communicator.wait_for_auth()

        # Verify authentication failed
        self.assertEqual(auth_message.payload.status_code, 403)

        # Connection should be closed
        await communicator.assert_closed()

Testing Utilities
-----------------
Chanx's testing utilities extend Django's testing tools with async support:

.. code-block:: python

    from chanx.utils.settings import override_chanx_settings

    # Test with different Chanx settings
    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_with_custom_settings(self):
        # SEND_COMPLETION will be True within this test
        pass

Best Practices
--------------
1. **Test both success and failure** paths
2. **Test authentication** thoroughly, including failure cases
3. **Test message validation** by sending invalid messages
4. **Test group messaging** with multiple communicators
5. **Test lifecycle events** like connection, disconnection, and errors
6. **Use async functions** with `async def test_*` naming
7. **Clean up connections** properly (WebsocketTestCase handles this)
8. **Mock external services** to isolate your tests
9. **Use transaction isolation** to prevent test interference

Next Steps
----------
- :doc:`../examples/chat` - See complete testing examples
- :doc:`playground` - Learn about the WebSocket playground for manual testing
