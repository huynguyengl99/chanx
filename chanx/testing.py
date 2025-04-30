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

    Provides additional helper methods for sending structured messages,
    receiving responses, handling authentication, and managing connections.
    """

    def __init__(
        self,
        application: Any,
        path: str,
        headers: list[tuple[bytes, bytes]] | None = None,
        subprotocols: list[str] | None = None,
        spec_version: int | None = None,
    ) -> None:
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
        messages: list[dict[str, Any]] = []
        async with async_timeout(timeout):
            while True:
                message = await self.receive_json_from(timeout)
                message_action = message.get(chanx_settings.MESSAGE_ACTION_KEY)
                if message_action == ACTION_COMPLETE:
                    if not wait_group:
                        break
                    else:
                        continue
                elif wait_group and message_action == GROUP_ACTION_COMPLETE:
                    break
                messages.append(message)
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
    Base test case for WebSocket testing.

    Subclass this and set the 'ws_path' class attribute to the WebSocket
    endpoint path for your tests. The router is automatically discovered
    from the ASGI application.
    """

    ws_path: str = ""
    router: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the test case and discovers the WebSocket router."""
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
        """Sets up test environment before each test method."""
        super().setUp()
        self.ws_headers: list[tuple[bytes, bytes]] = self.get_ws_headers()
        self.subprotocols: list[str] = self.get_subprotocols()
        self._communicators = []

    def tearDown(self) -> None:
        """Cleans up after each test, ensuring all WebSocket connections are closed."""
        for communicator in self._communicators:
            try:
                async_to_sync(communicator.disconnect)()
            except Exception:  # noqa
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
        Creates a WebsocketCommunicator with the given parameters.

        Args:
            router: Application to use (defaults to self.router)
            ws_path: WebSocket path to connect to (defaults to self.ws_path)
            headers: HTTP headers to include (defaults to self.ws_headers)
            subprotocols: WebSocket subprotocols to use (defaults to self.subprotocols)

        Returns:
            A configured WebsocketCommunicator instance
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
