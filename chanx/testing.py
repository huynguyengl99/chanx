"""
WebSocket testing utilities for Chanx.

This module provides specialized test infrastructure for WebSocket consumers,
including an extended WebsocketCommunicator and a base WebsocketTestCase class.
These utilities make it easier to write tests for WebSocket consumers by
providing helper methods for authentication handling, message sending/receiving,
and automatic cleanup. The module builds on Django's test framework and Channels'
testing components.
"""

import asyncio
from asyncio import CancelledError
from types import ModuleType
from typing import Any, cast

from channels.testing import WebsocketCommunicator as BaseWebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework import status

from asgiref.sync import async_to_sync
from asgiref.timeout import timeout as async_timeout

from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import (
    ACTION_COMPLETE,
    GROUP_ACTION_COMPLETE,
    AuthenticationMessage,
)
from chanx.settings import chanx_settings
from chanx.utils.asgi import get_websocket_application

try:
    import humps
except ImportError:  # pragma: no cover
    humps = cast(ModuleType, None)  # pragma: no cover


class WebsocketCommunicator(BaseWebsocketCommunicator):
    """
    Chanx extended WebsocketCommunicator for testing WebSocket consumers.

    Provides enhanced testing capabilities for WebSocket applications including:

    - Structured message sending and receiving

    - Authentication handling and verification

    - Automatic message collection until completion signals

    - Group message broadcast testing

    - Connection state tracking

    - Message validation and error handling

    Typical usage patterns:

    - Connection testing: connect(), assert_authenticated_status_ok()

    - Message exchange: send_message(), receive_all_json()

    - Authentication flows: wait_for_auth(), assert_authenticated_status_ok()

    - Error handling: send invalid messages and check error responses

    - Group messaging: create multiple communicators and test broadcasts

    The communicator automatically handles message serialization/deserialization
    and provides convenience methods to simplify common WebSocket testing tasks.
    """

    def __init__(
        self,
        application: Any,
        path: str,
        headers: list[tuple[bytes, bytes]] | None = None,
        subprotocols: list[str] | None = None,
        spec_version: int | None = None,
    ) -> None:
        """
        Initialize the WebSocket communicator for testing.

        Sets up the communicator with the specified application and path,
        and initializes connection tracking.

        Args:
            application: The ASGI application (usually a consumer)
            path: The WebSocket path to connect to
            headers: Optional HTTP headers for the connection
            subprotocols: Optional WebSocket subprotocols
            spec_version: Optional WebSocket spec version
        """
        super().__init__(application, path, headers, subprotocols, spec_version)
        self._connected = False

    async def receive_all_json(
        self, timeout: float = 5, *, wait_group: bool = False
    ) -> list[dict[str, Any]]:
        """
        Receives and collects all JSON messages until an ACTION_COMPLETE message
        is received or timeout occurs.

        Args:
            timeout: Maximum time to wait for messages (in seconds)
            wait_group: wait until the complete group messages are received

        Returns:
            List of received JSON messages
        """
        stop_action = GROUP_ACTION_COMPLETE if wait_group else ACTION_COMPLETE
        return await self.receive_until_action(stop_action, timeout=timeout)

    async def receive_until_action(
        self, stop_action: str, timeout: float = 5, *, inclusive: bool = False
    ) -> list[dict[str, Any]]:
        """
        Receives and collects JSON messages until a specific action is received.

        Automatically filters out completion messages (ACTION_COMPLETE and GROUP_ACTION_COMPLETE).

        Args:
            stop_action: The action type to stop collecting at
            timeout: Maximum time to wait for messages (in seconds)
            inclusive: Whether to include the stop_action message in results

        Returns:
            List of received JSON messages (excluding completion messages)
        """
        messages: list[dict[str, Any]] = []
        completion_actions = {ACTION_COMPLETE, GROUP_ACTION_COMPLETE}
        if not inclusive:
            completion_actions.add(stop_action)

        async with async_timeout(timeout):
            while True:
                message = await self.receive_json_from(timeout)
                message_action = message.get(chanx_settings.MESSAGE_ACTION_KEY)

                if message_action not in completion_actions:
                    messages.append(message)

                if message_action == stop_action:
                    break

        return messages

    async def send_message(self, message: BaseMessage) -> None:
        """
        Sends a Message object as JSON to the WebSocket.

        Args:
            message: The Message instance to send
        """
        await self.send_json_to(message.model_dump())

    async def wait_for_auth(
        self,
        send_authentication_message: bool | None = None,
        max_auth_time: float = 0.5,
        after_auth_time: float = 0.1,
    ) -> AuthenticationMessage | None:
        """
        Waits for and returns an authentication message if enabled in settings.

        Args:
            send_authentication_message: Whether to expect auth message, defaults to setting
            max_auth_time: Maximum time to wait for authentication (in seconds)
            after_auth_time: Wait time sleep after authentication (in seconds)

        Returns:
            Authentication message or None if auth is disabled
        """
        if send_authentication_message is None:
            send_authentication_message = chanx_settings.SEND_AUTHENTICATION_MESSAGE

        if send_authentication_message:
            json_message = await self.receive_json_from(max_auth_time)
            if chanx_settings.CAMELIZE:
                json_message = humps.decamelize(json_message)
            # make sure any other pending work still have chance to done after that
            await asyncio.sleep(after_auth_time)
            return AuthenticationMessage.model_validate(json_message)
        else:
            await asyncio.sleep(max_auth_time)
            return None

    async def assert_authenticated_status_ok(self, max_auth_time: float = 0.5) -> None:
        """
        Assert that the WebSocket connection was authenticated successfully.

        Waits for an authentication message and verifies that its status code is 200 OK.

        Args:
            max_auth_time: Maximum time to wait for authentication message (in seconds)

        Raises:
            AssertionError: If the authentication status is not 200 OK
        """
        auth_message = cast(
            AuthenticationMessage, await self.wait_for_auth(max_auth_time=max_auth_time)
        )
        assert auth_message.payload.status_code == status.HTTP_200_OK

    async def assert_closed(self) -> None:
        """Asserts that the WebSocket has been closed."""
        closed_status = await self.receive_output()
        assert closed_status == {"type": "websocket.close"}

    async def connect(self, timeout: float = 1) -> tuple[bool, int | str | None]:
        """
        Connects to the WebSocket and tracks connection state.

        Args:
            timeout: Maximum time to wait for connection (in seconds)

        Returns:
            Tuple of (connected, status_code)
        """
        try:
            res = await super().connect(timeout)
            self._connected = True
            return res
        except:
            raise


class WebsocketTestCase(TransactionTestCase):
    """
    Base test case for WebSocket testing with Chanx.

    Provides a framework for testing WebSocket consumers with built-in support for:

    - Automatic WebSocket application discovery

    - Connection management and cleanup

    - Authentication testing

    - Message sending and receiving

    - Group broadcast testing

    To use this class:

    1. Subclass WebsocketTestCase

    2. Set the ws_path class attribute to your WebSocket endpoint

    3. Optionally override get_ws_headers() for authentication

    4. Use self.auth_communicator for the main connection

    5. Use create_communicator() only when testing multi-user scenarios

    Attributes:
        ws_path: WebSocket endpoint path to test (required)
        router: WebSocket application router (auto-discovered)
        auth_communicator: Default WebSocket communicator for the main connection
    """

    ws_path: str = ""
    router: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the WebSocket test case.

        Discovers the WebSocket router from the ASGI application and
        initializes tracking for WebSocket communicators that need cleanup.

        Args:
            *args: Arguments passed to the parent TransactionTestCase
            **kwargs: Keyword arguments passed to the parent TransactionTestCase

        Raises:
            ValueError: If no WebSocket application could be discovered
        """
        super().__init__(*args, **kwargs)

        self._communicators: list[WebsocketCommunicator] = []

        if not self.router:
            # First try to get the complete WebSocket application with middleware
            ws_app = get_websocket_application()
            if ws_app:
                self.router = ws_app
            else:
                raise ValueError(
                    "Could not obtain a WebSocket application. Make sure your ASGI application is properly configured"
                    " with a 'websocket' handler in the ProtocolTypeRouter."
                )

    def get_ws_headers(self) -> list[tuple[bytes, bytes]]:
        """
        Returns WebSocket headers for authentication/configuration.
        Override this method to provide custom headers.
        """
        return []

    def get_subprotocols(self) -> list[str]:
        """
        Returns WebSocket subprotocols to use.
        Override this method to provide custom subprotocols.
        """
        return []

    def setUp(self) -> None:
        """
        Set up the test environment before each test method.

        Initializes WebSocket headers and subprotocols by calling the
        corresponding getter methods, and prepares for tracking communicators.
        """
        super().setUp()
        self.ws_headers: list[tuple[bytes, bytes]] = self.get_ws_headers()
        self.subprotocols: list[str] = self.get_subprotocols()
        self._communicators = []

    def tearDown(self) -> None:
        """
        Clean up after each test method.

        Ensures all WebSocket connections created during the test are properly
        disconnected to prevent resource leaks and test isolation issues.
        """
        for communicator in self._communicators:
            try:
                async_to_sync(communicator.disconnect)()
            except (Exception, CancelledError):  # noqa
                pass
        self._communicators = []

    def create_communicator(
        self,
        *,
        router: Any | None = None,
        ws_path: str | None = None,
        headers: list[tuple[bytes, bytes]] | None = None,
        subprotocols: list[str] | None = None,
    ) -> WebsocketCommunicator:
        """
        Creates a WebsocketCommunicator for testing WebSocket connections.

        Creates and tracks a communicator instance for interacting with WebSocket consumers
        in tests, allowing you to create multiple communicators to test various scenarios including:
        - Multi-user WebSocket interactions
        - Testing group message broadcasting
        - Testing authentication with different credentials
        - Simulating concurrent connections

        The method tracks all created communicators and automatically handles
        their cleanup during tearDown() to prevent resource leaks.

        Args:
            router: Application to use (defaults to self.router)
            ws_path: WebSocket path to connect to (defaults to self.ws_path)
            headers: HTTP headers to include (defaults to self.ws_headers)
                   Use different headers for testing multiple authenticated users
            subprotocols: WebSocket subprotocols to use (defaults to self.subprotocols)

        Returns:
            A configured WebsocketCommunicator instance ready for connecting

        Raises:
            AttributeError: If ws_path is not set and not provided
        """
        if router is None:
            router = self.router
        if ws_path is None:
            ws_path = self.ws_path
        if headers is None:
            headers = self.ws_headers
        if subprotocols is None:
            subprotocols = self.subprotocols

        if not ws_path:
            raise AttributeError(f"ws_path is not set in {self.__class__.__name__}")

        communicator = WebsocketCommunicator(
            router,
            ws_path,
            headers=headers,
            subprotocols=subprotocols,
        )

        # Track communicator for cleanup
        self._communicators.append(communicator)

        return communicator

    @property
    def auth_communicator(self) -> WebsocketCommunicator:
        """
        Returns a connected WebsocketCommunicator instance.
        The instance is created using create_communicator if not already exists.
        """
        if not self._communicators:
            self.create_communicator()

        return self._communicators[0]
