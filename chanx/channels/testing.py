"""
Django Channels integration for Chanx WebSocket testing.

This module extends Chanx's core testing utilities with Django-specific features,
including Django authentication integration, settings-based configuration,
and Django test framework compatibility. Provides DjangoWebsocketCommunicator
with authentication message handling and WebsocketTestCase for Django test
environments with automatic ASGI application discovery and cleanup.
"""

import asyncio
from asyncio import CancelledError
from typing import Any, cast

from channels.testing import WebsocketCommunicator as ChannelsWebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework import status

import humps
from asgiref.sync import async_to_sync

from chanx.channels.settings import chanx_settings
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.testing import WebsocketCommunicatorMixin
from chanx.messages.outgoing import AuthenticationMessage


class DjangoWebsocketCommunicator(
    WebsocketCommunicatorMixin, ChannelsWebsocketCommunicator
):
    """
    Django Channels WebSocket communicator for testing Chanx consumers.

    Combines Chanx testing mixin features with Django Channels' WebSocket communicator,
    providing both framework-agnostic and Django-specific testing capabilities:

    Chanx features (from WebsocketCommunicatorMixin):
    - Structured message sending/receiving with BaseMessage objects
    - Automatic message collection until completion signals
    - Message validation using consumer's type adapters
    - Async context manager support

    Django-specific features:
    - wait_for_auth(): Handle Django authentication messages
    - assert_authenticated_status_ok(): Validate DRF authentication status
    - Integration with Django settings (SEND_AUTHENTICATION_MESSAGE, CAMELIZE)
    - Automatic camelCase/snake_case conversion based on Django settings
    """

    application: Any
    consumer: type[AsyncJsonWebsocketConsumer]

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


class WebsocketTestCase(TransactionTestCase):
    """
    Django test case for WebSocket testing with Chanx.

    Integrates Chanx WebSocket testing with Django's test framework, providing:

    - Django TransactionTestCase inheritance for database transaction handling
    - Automatic Django ASGI application discovery from routing configuration
    - Django-style setUp/tearDown with automatic communicator cleanup
    - Integration with Django authentication headers via get_ws_headers()
    - Support for Django-specific WebSocket subprotocols

    Usage:
    1. Subclass WebsocketTestCase
    2. Set ws_path to your Django WebSocket endpoint
    3. Override get_ws_headers() for Django authentication
    4. Use self.auth_communicator for primary connection testing
    5. Use create_communicator() for multi-user Django scenarios

    The test case automatically discovers WebSocket routing from Django's ASGI
    configuration and ensures proper cleanup of all connections after each test.
    """

    ws_path: str = ""
    router: Any = None
    consumer: type[AsyncJsonWebsocketConsumer[Any]]

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

        self._communicators: list[DjangoWebsocketCommunicator] = []

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
    ) -> DjangoWebsocketCommunicator:
        """
        Creates a DjangoWebsocketCommunicator for testing WebSocket connections.

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
            A configured DjangoWebsocketCommunicator instance ready for connecting

        Raises:
            AttributeError: If ws_path is not set and not provided
        """
        if router is None:
            if self.router is not None:
                router = self.router
            else:
                from chanx.channels.utils import get_websocket_application

                ws_app = get_websocket_application()
                if ws_app:
                    router = ws_app
                else:
                    raise ValueError(
                        "Could not obtain a WebSocket application. Make sure your ASGI application is properly configured"
                        " with a 'websocket' handler in the ProtocolTypeRouter."
                    )
        if ws_path is None:
            ws_path = self.ws_path
        if headers is None:
            headers = self.ws_headers
        if subprotocols is None:
            subprotocols = self.subprotocols

        if not ws_path:
            raise AttributeError(f"ws_path is not set in {self.__class__.__name__}")

        assert router
        communicator = DjangoWebsocketCommunicator(
            router,
            ws_path,
            headers=headers,
            subprotocols=subprotocols,
            consumer=self.consumer,
        )

        # Track communicator for cleanup
        self._communicators.append(communicator)

        return communicator

    @property
    def auth_communicator(self) -> DjangoWebsocketCommunicator:
        """
        Returns a connected DjangoWebsocketCommunicator instance.
        The instance is created using create_communicator if not already exists.
        """
        if not self._communicators:
            self.create_communicator()

        return self._communicators[0]
