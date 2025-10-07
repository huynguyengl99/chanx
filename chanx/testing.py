"""
Core WebSocket testing utilities for Chanx.

This module provides fundamental testing infrastructure for WebSocket consumers,
including an enhanced WebsocketCommunicator with structured message handling,
automatic message collection, completion signal tracking, and message validation.
These utilities work with any ASGI application and provide the foundation for
framework-specific testing extensions.
"""

import asyncio
from types import TracebackType
from typing import Any, Self

import humps
from asgiref.timeout import timeout as async_timeout

from chanx.constants import (
    COMPLETE_ACTIONS,
    COMPLETE_ACTIONS_TYPE,
    MESSAGE_ACTION_COMPLETE,
)
from chanx.core.adapter import WebsocketCommunicator as BaseWebsocketCommunicator
from chanx.core.config import config
from chanx.core.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage


class WebsocketCommunicator(BaseWebsocketCommunicator):
    """
    Enhanced WebSocket communicator for testing Chanx consumers.

    Extends the base WebSocket communicator with Chanx-specific features:

    - Structured message sending and receiving with BaseMessage objects
    - Automatic message collection until completion signals
    - Message validation using consumer's type adapters
    - Connection state tracking
    - Async context manager support for automatic cleanup

    Key methods:
    - send_message(): Send BaseMessage objects directly
    - receive_all_json(): Collect all messages until timeout
    - receive_all_messages(): Collect and validate messages until stop action
    - connect()/disconnect(): Enhanced connection management

    The communicator automatically handles message serialization/deserialization
    and integrates with Chanx's completion signal system for reliable testing.
    """

    application: Any
    action_key: str = "action"
    consumer: type[AsyncJsonWebsocketConsumer[Any]]

    def __init__(
        self,
        application: Any,
        path: str,
        headers: list[tuple[bytes, bytes]] | None = None,
        subprotocols: list[str] | None = None,
        spec_version: int | None = None,
        *,
        consumer: type[AsyncJsonWebsocketConsumer[Any]],
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

        self.consumer = consumer

    async def receive_all_json(self, timeout: float = 1) -> list[dict[str, Any]]:
        """
        Receives and collects all JSON messages until an ACTION_COMPLETE message
        is received or timeout occurs.

        Args:
            timeout: Maximum time to wait for messages (in seconds)

        Returns:
            List of received JSON messages
        """
        json_list: list[dict[str, Any]] = []
        try:
            async with async_timeout(timeout):
                while True:
                    raw_message = await self.receive_json_from(timeout)
                    json_list.append(raw_message)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

        return json_list

    async def receive_all_messages(
        self,
        stop_action: COMPLETE_ACTIONS_TYPE | str = MESSAGE_ACTION_COMPLETE,
        timeout: float = 1,
    ) -> list[BaseMessage]:
        """
        Receives and collects JSON messages until a specific action is received.

        Automatically filters out completion messages (ACTION_COMPLETE and GROUP_ACTION_COMPLETE).

        Args:
            stop_action: The action type to stop collecting at
            timeout: Maximum time to wait for messages (in seconds)

        Returns:
            List of received JSON messages (excluding completion messages)
        """
        if not self.consumer:
            raise ValueError("consumer must be initialized to use this method")

        messages: list[BaseMessage] = []

        try:
            async with async_timeout(timeout):
                while True:
                    raw_message = await self.receive_json_from(timeout)

                    if getattr(self.consumer, "camelize", False) or config.camelize:
                        raw_message = humps.decamelize(raw_message)

                    message_action = raw_message.get(self.action_key)

                    if message_action not in COMPLETE_ACTIONS:
                        message = (
                            self.consumer.outgoing_message_adapter.validate_python(
                                raw_message
                            )
                        )
                        messages.append(message)

                    if message_action == stop_action:
                        break
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        return messages

    async def send_message(self, message: BaseMessage) -> None:
        """
        Sends a Message object as JSON to the WebSocket.

        Args:
            message: The Message instance to send
        """
        await self.send_json_to(message.model_dump())

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

    async def disconnect(self, code: int = 1000, timeout: float = 1) -> None:
        """
        Closes the socket

        Args:
            code: Optional code to disconnect
            timeout: Maximum time to wait for connection (in seconds)
        """
        try:
            await super().disconnect(code, timeout)
        except asyncio.CancelledError:
            pass

    async def __aenter__(self) -> Self:
        """Async context manager entry - connects to WebSocket."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit - disconnects from WebSocket."""
        await self.disconnect()
