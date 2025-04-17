import asyncio
from typing import Any

from channels.testing import WebsocketCommunicator as BaseWebsocketCommunicator
from django.test import TransactionTestCase

from asgiref.sync import async_to_sync
from asgiref.timeout import timeout as async_timeout

from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import ACTION_COMPLETE, AuthenticationMessage
from chanx.settings import chanx_settings
from chanx.utils.asgi import get_websocket_application


class WebsocketCommunicator(BaseWebsocketCommunicator):  # type: ignore
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
        spec_version: str | None = None,
    ) -> None:
        super().__init__(application, path, headers, subprotocols, spec_version)
        self.connected = False

    async def receive_all_json(self, timeout: int = 5) -> list[dict[str, Any]]:
        """
        Receives and collects all JSON messages until an ACTION_COMPLETE message
        is received or timeout occurs.

        Args:
            timeout: Maximum time to wait for messages (in seconds)

        Returns:
            List of received JSON messages
        """
        messages: list[dict[str, Any]] = []
        async with async_timeout(timeout):
            while True:
                message = await self.receive_json_from(timeout)
                message_action = message.get(chanx_settings.MESSAGE_ACTION_KEY)
                if message_action == ACTION_COMPLETE:
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
        self, send_authentication_message: bool | None = None, max_auth_time: float = 1
    ) -> AuthenticationMessage | None:
        """
        Waits for and returns an authentication message if enabled in settings.

        Args:
            send_authentication_message: Whether to expect auth message, defaults to setting
            max_auth_time: Maximum time to wait for authentication (in seconds)

        Returns:
            Authentication message or None if auth is disabled
        """
        if send_authentication_message is None:
            send_authentication_message = chanx_settings.SEND_AUTHENTICATION_MESSAGE

        if send_authentication_message:
            json_message = await self.receive_json_from(max_auth_time)
            return AuthenticationMessage.model_validate(json_message)
        else:
            await asyncio.sleep(max_auth_time)
            return None

    async def assert_closed(self) -> None:
        """Asserts that the WebSocket has been closed."""
        closed_status = await self.receive_output()
        assert closed_status == {"type": "websocket.close"}

    async def connect(self, timeout: float = 1) -> tuple[bool, int]:
        """
        Connects to the WebSocket and tracks connection state.

        Args:
            timeout: Maximum time to wait for connection (in seconds)

        Returns:
            Tuple of (connected, status_code)
        """
        try:
            res: tuple[bool, int] = await super().connect(timeout)
            self.connected = True
            return res
        except:
            raise

    @property
    def is_alive(self) -> bool:
        """Returns whether the WebSocket connection is still alive."""
        return self.future.done() and self.connected


class WebsocketTestCase(TransactionTestCase):
    """
    Base test case for WebSocket testing.

    Subclass this and set the 'ws_path' class attribute to the WebSocket
    endpoint path for your tests. The router is automatically discovered
    from the ASGI application.
    """

    ws_path: str
    router: Any = None

    @classmethod
    def setUpClass(cls) -> None:
        """Ensures ws_path is set in the subclass."""
        super().setUpClass()
        if not hasattr(cls, "ws_path"):
            raise AttributeError(f"ws_path is not set in {cls.__name__}")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the test case and discovers the WebSocket router."""
        super().__init__(*args, **kwargs)

        self._auth_communicator_instance: WebsocketCommunicator | None = None

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
        self._auth_communicator_instance = None

    def tearDown(self) -> None:
        """Cleans up after each test, ensuring WebSocket connections are closed."""
        if (
            self._auth_communicator_instance
            and self._auth_communicator_instance.is_alive
        ):
            async_to_sync(self._auth_communicator_instance.disconnect)()
        self._auth_communicator_instance = None

    @property
    def auth_communicator(self) -> WebsocketCommunicator:
        """
        Returns a connected WebsocketCommunicator instance.
        The instance is created only once per test method.
        """
        if not self._auth_communicator_instance:
            self._auth_communicator_instance = WebsocketCommunicator(
                self.router,
                self.ws_path,
                headers=self.ws_headers,
                subprotocols=self.subprotocols,
            )

        return self._auth_communicator_instance
