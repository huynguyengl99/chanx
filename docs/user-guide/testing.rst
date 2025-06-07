Testing
=======
Chanx provides specialized testing utilities that make it easier to write comprehensive tests for WebSocket consumers. These tools handle connection management, authentication, message exchange, and test cleanup.

Testing Configuration
---------------------
Before writing tests, configure your test settings for optimal testing performance:

.. code-block:: python

    # settings/test.py or in your test configuration
    CHANX = {
        "SEND_COMPLETION": True,  # Essential for receive_all_json() to work properly
        "SEND_AUTHENTICATION_MESSAGE": True,  # Recommended for testing authentication flows
        "LOG_RECEIVED_MESSAGE": False,  # Optional: reduce test output
        "LOG_SENT_MESSAGE": False,  # Optional: reduce test output
    }

**Important**: Setting `SEND_COMPLETION: True` is crucial for testing. The `receive_all_json()` method relies on
completion messages to know when to stop collecting messages, ensuring your tests receive all expected messages
before assertions.

Testing Overview
----------------
Testing WebSocket consumers differs from testing regular HTTP views:

1. Connections are long-lived instead of request/response
2. Authentication happens once at connection time
3. Multiple messages can be exchanged over a single connection
4. Asynchronous code requires special testing approaches
5. Group messaging requires multiple client testing

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
            # Use the default authenticator communicator
            await self.auth_communicator.connect()

            # Verify connection was successful
            await self.auth_communicator.assert_authenticated_status_ok()

Key features of `WebsocketTestCase`:

1. **Automatic Router Discovery**: Finds your WebSocket application from ASGI configuration
2. **Connection Tracking**: Manages test communicators to ensure proper cleanup
3. **Helper Methods**: Provides utilities for common testing tasks
4. **Default auth_communicator**: Access the main communicator via `self.auth_communicator`
5. **Multi-user testing support**: Create additional communicators as needed

Authentication in Testing
-------------------------
There are several ways to implement authentication in your tests. Here's an example of JWT-based authentication in a custom test case:

.. code-block:: python

    from django.conf import settings
    from accounts.factories.user import UserFactory
    from accounts.models import User
    from asgiref.sync import sync_to_async
    from chanx.testing import WebsocketTestCase as BaseWebsocketTestCase
    from rest_framework_simplejwt.tokens import RefreshToken


    class WebsocketTestCase(BaseWebsocketTestCase):
        def setUp(self) -> None:
            # Create a user and authentication headers during setup
            self.user, self.ws_headers = self.create_user_and_ws_headers()
            super().setUp()

        def create_user_and_ws_headers(self) -> tuple[User, list[tuple[bytes, bytes]]]:
            # Create a user and generate JWT tokens
            user = UserFactory.create()
            user_refresh_token = RefreshToken.for_user(user)

            # Create cookie string with JWT tokens
            cookie_string = (
                f"jwt_auth_cookie={str(user_refresh_token.access_token)}; "
                f"jwt_auth_refresh_cookie={str(user_refresh_token)}"
            )

            # Create WebSocket headers with the cookie and other required headers
            ws_headers = [
                (b"cookie", cookie_string.encode()),
                (b"origin", settings.SERVER_URL.encode()),
                (b"x-forwarded-for", b"127.0.0.1"),
            ]
            return user, ws_headers

        async def acreate_user_and_ws_headers(self) -> tuple[User, list[tuple[bytes, bytes]]]:
            """Async version for creating users during tests"""
            return await sync_to_async(self.create_user_and_ws_headers)()

        def get_ws_headers(self) -> list[tuple[bytes, bytes]]:
            """Provide headers for the default auth_communicator"""
            return self.ws_headers

For session-based authentication, you can use Django's test client:

.. code-block:: python

    def get_ws_headers(self):
        # Create a session using Django's test client
        self.client.login(username="testuser", password="password")

        # Get the session cookie
        cookies = self.client.cookies
        return [
            (b"cookie", f"sessionid={cookies['sessionid'].value}".encode()),
        ]

Creating Multiple Communicators
-------------------------------
For testing scenarios with multiple users, use the `create_communicator` method:

.. code-block:: python

    async def test_multi_user_scenario(self) -> None:
        # Get the default communicator for the first user
        first_comm = self.auth_communicator

        # Create a second user with different auth headers
        second_user, second_ws_headers = await self.acreate_user_and_ws_headers()

        # Create a communicator for the second user
        second_comm = self.create_communicator(
            headers=second_ws_headers,
        )

        # Connect both communicators
        await first_comm.connect()
        await first_comm.assert_authenticated_status_ok()

        await second_comm.connect()
        await second_comm.assert_authenticated_status_ok()

        # Test interactions between the users
        # ...

The `create_communicator` method is essential for multi-user testing. It:

- Creates WebsocketCommunicator instances with custom configuration
- Automatically tracks communicators for proper cleanup
- Supports custom headers for authentication
- Lets you test group messaging scenarios

WebsocketCommunicator Features
------------------------------
Chanx extends the standard Channels WebsocketCommunicator with additional features:

.. code-block:: python

    # Connect with timeout
    connected, _ = await communicator.connect(timeout=3)

    # Wait for authentication message
    auth_message = await communicator.wait_for_auth()

    # Assert authentication succeeded
    await communicator.assert_authenticated_status_ok()

    # Send message objects directly
    from myapp.messages import ChatMessage
    await communicator.send_message(ChatMessage(payload="Hello"))

    # Receive all messages until completion
    # NOTE: Requires SEND_COMPLETION=True in test settings
    messages = await communicator.receive_all_json()

    # Receive messages including group completion
    # NOTE: Also requires SEND_COMPLETION=True
    messages = await communicator.receive_all_json(wait_group=True)

    # Receive messages until a specific action
    # Useful for streaming responses or custom completion signals
    messages = await communicator.receive_until_action("streaming_complete")

    # Include the stop action in results
    messages = await communicator.receive_until_action("custom_end", inclusive=True)

    # Verify connection closed properly
    await communicator.assert_closed()

Testing Message Exchange
------------------------
Here's a complete example of testing message exchange with modern Python assertions:

.. code-block:: python

    from typing import Any, cast
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage
    from myapp.messages import ChatMessage, ChatResponse

    class TestChatConsumer(WebsocketTestCase):
        ws_path = "/ws/chat/room1/"

        async def test_ping_pong(self) -> None:
            # Connect and authenticate
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            # Send ping message
            await self.auth_communicator.send_message(PingMessage())

            # Receive all messages until completion
            responses = await self.auth_communicator.receive_all_json()

            # Check for pong response
            assert len(responses) == 1

            # You can either check raw JSON
            assert responses[0]["action"] == "pong"

            # Or validate with the message model
            pong_message = PongMessage.model_validate(responses[0])
            assert isinstance(pong_message, PongMessage)

        async def test_chat_message(self) -> None:
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            # Send chat message
            message_content = "Test message"
            await self.auth_communicator.send_message(
                ChatMessage(payload={"content": message_content})
            )

            # Get responses up to completion marker
            responses = await self.auth_communicator.receive_all_json()

            # Verify the response
            assert len(responses) == 1
            response = responses[0]
            assert response["action"] == "chat_response"
            assert response["payload"]["content"] == f"Echo: {message_content}"

        async def test_multi_step_process(self) -> None:
            """Test a multi-step process with custom completion signal"""
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            # Start a complex process
            await self.auth_communicator.send_message(
                ComplexProcessMessage(payload={"steps": 5})
            )

            # Collect messages until the process completes
            messages = await self.auth_communicator.receive_until_action("process_finished")

            # Verify all steps were completed
            step_messages = [msg for msg in messages if msg["action"] == "step_completed"]
            assert len(step_messages) == 5

Testing Group Messaging
-----------------------
Use multiple communicators to test group messaging:

.. code-block:: python

    async def test_group_message_broadcast(self) -> None:
        """Test that messages are broadcast to all group members"""
        # Create a second user with different auth headers
        second_user, second_ws_headers = await self.acreate_user_and_ws_headers()

        # Create communicators for both users in the same room
        first_comm = self.auth_communicator
        second_comm = self.create_communicator(headers=second_ws_headers)

        # Connect both communicators
        await first_comm.connect()
        await first_comm.assert_authenticated_status_ok()

        await second_comm.connect()
        await second_comm.assert_authenticated_status_ok()

        # Send a message from the first user
        message_content = "This is a group message"
        await first_comm.send_message(
            ChatMessage(payload={"content": message_content})
        )

        # Verify that the first user (sender) receives the message
        first_responses = await first_comm.receive_all_json(wait_group=True)
        assert len(first_responses) == 1
        assert first_responses[0]["action"] == "chat_group"
        assert first_responses[0]["payload"]["content"] == message_content
        assert first_responses[0]["is_mine"] == True  # Sent by this user

        # Verify that the second user receives the same message
        second_responses = await second_comm.receive_all_json(wait_group=True)
        assert len(second_responses) == 1
        assert second_responses[0]["action"] == "chat_group"
        assert second_responses[0]["payload"]["content"] == message_content
        assert second_responses[0]["is_mine"] == False  # Not sent by this user

Testing Object Permissions
--------------------------
Test consumer access with object-level permissions:

.. code-block:: python

    async def test_room_access_permission(self) -> None:
        """Test that only room members can access the room consumer"""
        # Create a room and add the default user as a member
        room = await Room.objects.acreate(name="Test Room")
        await RoomMember.objects.acreate(room=room, user=self.user)

        # Create a non-member user
        non_member, non_member_headers = await self.acreate_user_and_ws_headers()

        # Test successful access with member
        member_comm = self.auth_communicator
        room_path = f"/ws/rooms/{room.id}/"
        connected, _ = await member_comm.connect(ws_path=room_path)
        assert connected == True

        # Verify authentication succeeded
        auth_message = await member_comm.wait_for_auth()
        assert auth_message.payload.status_code == 200

        # Test failed access with non-member
        non_member_comm = self.create_communicator(headers=non_member_headers)
        connected, _ = await non_member_comm.connect(ws_path=room_path)
        assert connected == True  # Initial connection succeeds

        # But authentication fails due to permission check
        auth_message = await non_member_comm.wait_for_auth()
        assert auth_message.payload.status_code == 403

        # Connection should be closed
        await non_member_comm.assert_closed()

Mocking in WebSocket Tests
--------------------------
For isolated tests, mock external dependencies:

.. code-block:: python

    from unittest.mock import patch, AsyncMock

    async def test_database_integration(self) -> None:
        # Mock the database operation
        with patch('myapp.services.message_service.save_message') as mock_save:
            mock_save.return_value = AsyncMock(id=123, content="Test")

            # Connect and send a message
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            await self.auth_communicator.send_message(
                ChatMessage(payload={"content": "Test message"})
            )

            # Verify the mock was called
            mock_save.assert_called_once()
            args, kwargs = mock_save.call_args
            assert kwargs["content"] == "Test message"

            # Check response
            responses = await self.auth_communicator.receive_all_json()
            assert len(responses) == 1

Testing Custom Apps
-------------------
Here's a complete example of a test for a chat application with custom test case:

.. code-block:: python

    from typing import Any, cast
    from chanx.testing import WebsocketTestCase
    from chat.messages.chat import ChatIncomingMessage, NewChatMessage, MessagePayload
    from chat.messages.group import MemberMessage
    from chat.models import ChatMember, ChatMessage, GroupChat

    class ChatTestCase(WebsocketTestCase):
        async def setUp(self) -> None:
            await super().setUp()
            # Create a group chat and add the user as a member
            self.group_chat = await GroupChat.objects.acreate(name="Test Group")
            self.member = await ChatMember.objects.acreate(
                user=self.user,
                group_chat=self.group_chat,
                chat_role=ChatMember.ChatMemberRole.ADMIN,
            )

        async def test_connect_and_send_message(self) -> None:
            """Test connection and sending a message to a group chat"""
            # Connect to the chat endpoint
            self.ws_path = f"/ws/chat/{self.group_chat.pk}/"
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            # Test sending a chat message
            message_content = "Hello group chat!"
            await self.auth_communicator.send_message(
                NewChatMessage(payload=MessagePayload(content=message_content))
            )

            # Receive the message that was broadcast
            messages = await self.auth_communicator.receive_all_json(wait_group=True)

            # Check the message was received and has the correct content
            assert len(messages) == 1
            assert messages[0]["action"] == "member_message"
            assert messages[0]["payload"]["content"] == message_content

            # Verify the message was stored in the database
            db_messages = await ChatMessage.objects.acount()
            assert db_messages == 1

Comparison of Message Collection Methods
----------------------------------------
Choose the right method for your testing needs:

.. code-block:: python

    # Standard completion-based collection
    # Use for: Simple request-response patterns
    messages = await communicator.receive_all_json()

    # Group message completion-based collection
    # Use for: Group broadcasts and pub/sub patterns
    messages = await communicator.receive_all_json(wait_group=True)

    # Custom action-based collection
    # Use for: Streaming, multi-step processes, custom protocols
    messages = await communicator.receive_until_action("my_completion_action")

    # Include completion message in results
    # Use for: Debugging, testing completion message format
    all_messages = await communicator.receive_until_action("done", inclusive=True)

Best Practices
--------------
1. **Subclass WebsocketTestCase**: Create a custom test base class for your app
2. **Configure test settings**: Set `SEND_COMPLETION=True` in test environment for proper message collection
3. **Set up authenticating fixtures**: Provide proper authentication in setUp
4. **Use modern assert statements**: Use Python's built-in assert for cleaner tests
5. **Test both success and failure**: Verify both positive and negative cases
6. **Test group broadcasts**: Create multiple communicators to test group messaging
7. **Use wait_group=True**: When testing group messages, use the wait_group parameter
8. **Choose the right collection method**: Use `receive_until_action` for streaming or custom protocols
9. **Mock external services**: Use AsyncMock for external dependencies
10. **Test database persistence**: Verify messages are properly stored/retrieved
11. **Test lifecycle events**: Check connections, authentication, and disconnections
12. **Use async test methods**: Write all test methods as async coroutines
13. **Disable verbose logging**: Set logging flags to False in test settings to reduce output

Next Steps
----------
- :doc:`consumers` - Learn about WebSocket consumers
- :doc:`messages` - Understand message validation
- :doc:`playground` - Try the interactive WebSocket playground
- :doc:`../examples/chat` - See complete test examples in the chat application
- :doc:`../reference/testing` - API reference for testing utilities and methods
