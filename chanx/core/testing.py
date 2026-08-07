"""
Core WebSocket testing utilities for Chanx.

This module provides fundamental testing infrastructure for WebSocket consumers,
including an enhanced WebsocketCommunicator mixin with structured message handling,
automatic message collection, completion signal tracking, and message validation.

The mixin provides framework-agnostic testing functionality that can be combined
with framework-specific WebSocket communicator implementations (Django Channels,
fast-channels, etc.) to create concrete testing utilities.
"""

import asyncio
from collections.abc import Collection, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self, cast

import humps
from asgiref.timeout import timeout as async_timeout

from chanx.constants import (
    COMPLETE_ACTIONS,
    COMPLETE_ACTIONS_TYPE,
    MESSAGE_ACTION_COMPLETE,
    MULTIPLEX_READY_ACTION,
)
from chanx.core.config import config
from chanx.core.multiplex import ChanxDemultiplexerMixin, is_demultiplexer
from chanx.core.websocket import ChanxWebsocketConsumerMixin
from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import MultiplexReadyMessage

# Protocol frames excluded from collected messages: they punctuate a conversation
# rather than belong to it. Assert on them with the dedicated helpers instead.
SKIPPED_ACTIONS = COMPLETE_ACTIONS | {MULTIPLEX_READY_ACTION}


@dataclass
class CapturedBroadcastEvent:
    """Structure of a captured broadcast event."""

    event: BaseMessage
    groups: Collection[str] | str | None


class WebsocketCommunicatorMixin:
    """
    Mixin providing enhanced WebSocket testing functionality for Chanx consumers.

    This mixin provides Chanx-specific features that work across different WebSocket
    frameworks (Django Channels, fast-channels, etc.):

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

    The mixin automatically handles message serialization/deserialization and integrates
    with Chanx's completion signal system for reliable testing.

    Concrete implementations should inherit from both this mixin and a framework-specific
    WebSocket communicator class (e.g., channels.testing.WebsocketCommunicator).
    """

    # These will be set by concrete implementations or during initialization
    application: Any
    action_key: str = "action"
    consumer: type[ChanxWebsocketConsumerMixin]  # Consumer class for message validation
    _connected: bool

    # Framework-provided methods (redefined for type checking)
    async def receive_json_from(self, timeout: float = 1) -> Any:
        """
        Receive and parse JSON data from the WebSocket.

        Provided by the framework testing communicator (Channels/fast-channels).

        Args:
            timeout: Maximum time to wait for data (seconds)

        Returns:
            Parsed JSON data as dictionary
        """
        return await super().receive_json_from(timeout)  # type: ignore[misc]

    async def send_json_to(self, data: dict[str, Any]) -> None:
        """
        Send JSON data to the WebSocket.

        Provided by the framework testing communicator (Channels/fast-channels).

        Args:
            data: Dictionary to serialize and send as JSON
        """
        await super().send_json_to(data)  # type: ignore[misc]

    async def receive_output(self, timeout: float = 1) -> Any:
        """
        Receive raw output from the WebSocket.

        Provided by the framework testing communicator (Channels/fast-channels).

        Args:
            timeout: Maximum time to wait for output (seconds)

        Returns:
            Raw output dictionary
        """
        return await super().receive_output(timeout)  # type: ignore[misc]

    def __init__(
        self,
        application: Any,
        path: str,
        headers: list[tuple[bytes, bytes]] | None = None,
        subprotocols: list[str] | None = None,
        spec_version: int | None = None,
        *,
        consumer: type[ChanxWebsocketConsumerMixin[Any]],
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
        super().__init__(application, path, headers, subprotocols, spec_version)  # type: ignore
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

    @property
    def demultiplexer(self) -> type[ChanxDemultiplexerMixin[Any]] | None:
        """
        The demultiplexer under test, or None when the consumer is not multiplexed.

        Returns:
            The demultiplexer class, or None for a single-consumer route
        """
        consumer = self.consumer
        return consumer if is_demultiplexer(consumer) else None

    def _unwrap_envelope(
        self, raw_message: dict[str, Any]
    ) -> tuple[str | None, dict[str, Any], type[ChanxWebsocketConsumerMixin[Any]]]:
        """
        Split a received frame into its consumer key, inner message and validator.

        For a single-consumer route, and for demultiplexer-level frames such as
        errors that are sent unwrapped, the frame is its own inner message and the
        communicator's consumer validates it.

        Args:
            raw_message: The raw JSON frame received from the WebSocket

        Returns:
            Tuple of (consumer key or None, inner message, validating consumer)
        """
        demultiplexer = self.demultiplexer
        if demultiplexer is None:
            return None, raw_message, self.consumer

        key = raw_message.get(demultiplexer.envelope_consumer_field)
        sub_consumer = (
            demultiplexer.consumers.get(key) if isinstance(key, str) else None
        )
        if key is None or sub_consumer is None:
            # Unwrapped frame, or an envelope for a consumer this demultiplexer
            # does not serve; either way the demultiplexer validates it.
            return None, raw_message, demultiplexer

        inner = cast(
            dict[str, Any], raw_message.get(demultiplexer.envelope_message_field) or {}
        )
        return key, inner, sub_consumer

    async def receive_all_envelopes(
        self,
        stop_action: COMPLETE_ACTIONS_TYPE | str = MESSAGE_ACTION_COMPLETE,
        timeout: float = 1,
        stop_consumer: str | None = None,
    ) -> list[tuple[str | None, BaseMessage]]:
        """
        Receives and collects messages together with the consumer that sent them.

        Behaves like receive_all_messages, but also reports which multiplexed
        consumer each message came from. The key is None for messages sent by a
        single-consumer route, and for demultiplexer-level messages such as errors.

        Args:
            stop_action: The action type to stop collecting at
            timeout: Maximum time to wait for messages (in seconds)
            stop_consumer: Only stop at stop_action when it comes from this
                           multiplexed consumer. Useful when several consumers
                           each send their own completion message.

        Returns:
            List of (consumer key, message) pairs, excluding completion messages
            and the multiplex_ready handshake
        """
        if not self.consumer:
            raise ValueError("consumer must be initialized to use this method")

        envelopes: list[tuple[str | None, BaseMessage]] = []

        try:
            async with async_timeout(timeout):
                while True:
                    raw_message = await self.receive_json_from(timeout)

                    key, inner, validator = self._unwrap_envelope(raw_message)

                    if getattr(validator, "camelize", False) or config.camelize:
                        inner = humps.decamelize(inner)

                    message_action = inner.get(self.action_key)

                    if message_action not in SKIPPED_ACTIONS:
                        message = validator.outgoing_message_adapter.validate_python(
                            inner
                        )
                        envelopes.append((key, message))

                    if message_action == stop_action and (
                        stop_consumer is None or key == stop_consumer
                    ):
                        break
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        return envelopes

    async def receive_all_messages(
        self,
        stop_action: COMPLETE_ACTIONS_TYPE | str = MESSAGE_ACTION_COMPLETE,
        timeout: float = 1,
        stop_consumer: str | None = None,
    ) -> list[BaseMessage]:
        """
        Receives and collects JSON messages until a specific action is received.

        Automatically filters out completion messages (ACTION_COMPLETE and GROUP_ACTION_COMPLETE).

        When the consumer under test is a demultiplexer, enveloped frames are
        unwrapped and each inner message is validated against the consumer it came
        from. Use receive_all_envelopes() when you also need to know which consumer
        sent each message.

        Args:
            stop_action: The action type to stop collecting at
            timeout: Maximum time to wait for messages (in seconds)
            stop_consumer: Only stop at stop_action when it comes from this
                           multiplexed consumer

        Returns:
            List of received JSON messages (excluding completion messages)
        """
        envelopes = await self.receive_all_envelopes(
            stop_action, timeout, stop_consumer
        )
        return [message for _key, message in envelopes]

    async def receive_multiplex_ready(
        self, timeout: float = 1
    ) -> MultiplexReadyMessage:
        """
        Receives the multiplex_ready handshake a demultiplexer sends on connect.

        Args:
            timeout: Maximum time to wait for the frame (in seconds)

        Returns:
            The MultiplexReadyMessage announcing which consumers are addressable

        Raises:
            ValueError: If the communicator is not testing a demultiplexer
            AssertionError: If the next frame is not the handshake
        """
        if self.demultiplexer is None:
            raise ValueError(
                f"{self.consumer.__name__} is not a demultiplexer"
                f" and never sends a multiplex_ready frame"
            )

        raw_message = await self.receive_json_from(timeout)
        assert (
            raw_message.get(self.action_key) == MULTIPLEX_READY_ACTION
        ), f"Expected a {MULTIPLEX_READY_ACTION} frame, got {raw_message!r}"
        return MultiplexReadyMessage.model_validate(raw_message)

    async def send_message(
        self, message: BaseMessage, *, consumer: str | None = None
    ) -> None:
        """
        Sends a Message object as JSON to the WebSocket.

        Args:
            message: The Message instance to send
            consumer: Multiplexed consumer key to address the message to. Requires
                      the communicator's consumer to be a demultiplexer. When
                      omitted the message is sent unwrapped, which reaches a
                      demultiplexer's own handlers.

        Raises:
            ValueError: If consumer is given but the communicator is not testing a
                        demultiplexer.
        """
        content: dict[str, Any] = message.model_dump()

        if consumer is not None:
            demultiplexer = self.demultiplexer
            if demultiplexer is None:
                raise ValueError(
                    f"Cannot address consumer {consumer!r}:"
                    f" {self.consumer.__name__} is not a demultiplexer"
                )
            content = {
                demultiplexer.envelope_version_field: demultiplexer.envelope_version,
                demultiplexer.envelope_consumer_field: consumer,
                demultiplexer.envelope_message_field: content,
            }

        await self.send_json_to(content)

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
            res = await super().connect(timeout)  # type: ignore
            self._connected = True
            return cast(tuple[bool, int | str | None], res)
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
            await super().disconnect(code, timeout)  # type: ignore
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


@contextmanager
def capture_broadcast_events(
    consumer: type[ChanxWebsocketConsumerMixin],
    suppress: bool = True,
) -> Generator[list[CapturedBroadcastEvent], None, None]:
    """
    Capture broadcast events sent via broadcast_event() for testing purposes.

    Similar to structlog's capture_logs(), this context manager captures calls to
    broadcast_event() by monkey-patching the broadcast_event method to spy on events.

    Args:
        consumer: The consumer class to capture broadcast events from.
        suppress: If True (default), suppress actual broadcast event calls.
                  If False, capture events and still call the original broadcast_event.

    Returns:
        A list that will be populated with captured broadcast events.
    """
    captured_events: list[CapturedBroadcastEvent] = []

    # Save the original broadcast_event method
    original_broadcast_event = consumer.broadcast_event

    # Create wrapper that captures events
    async def capture_wrapper(
        _cls: type[ChanxWebsocketConsumerMixin],
        event: BaseMessage,
        groups: Collection[str] | str | None = None,
    ) -> None:
        """Wrapper that captures the event before calling original."""

        # Capture the event directly
        captured_events.append(
            CapturedBroadcastEvent(
                event=event,
                groups=groups,
            )
        )

        # Only call original if not suppressing
        if not suppress:
            await original_broadcast_event(event, groups)

    # Monkey-patch the method
    consumer.broadcast_event = classmethod(capture_wrapper)  # type: ignore[method-assign, assignment]

    try:
        yield captured_events
    finally:
        # Restore original method
        consumer.broadcast_event = original_broadcast_event  # type: ignore[method-assign]
