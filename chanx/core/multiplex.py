"""
WebSocket multiplexing/demultiplexing for Chanx consumers.

This module provides the framework-agnostic ChanxDemultiplexerMixin, which lets a
single WebSocket route serve several consumers at once. Client frames carry a
small envelope naming the target sub-consumer, and the demultiplexer routes them
accordingly; frames produced by a sub-consumer are enveloped on the way back out.

    -> {"consumer": "echo", "message": {"action": "echo", "payload": {...}}}
    <- {"consumer": "echo", "message": {"action": "echo_reply", "payload": {...}}}

Each sub-consumer runs as a real consumer instance driven through the ASGI
protocol: it receives from a private queue owned by the demultiplexer and sends
through a wrapper that envelopes its frames. As a result every sub-consumer keeps
its own channel name and its own channel layer subscription, so groups,
``broadcast_message()``, ``broadcast_event()`` and ``@event_handler`` all behave
exactly as they do on a dedicated route. Sub-consumers need no changes to be
multiplexed.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeGuard, cast

import structlog
from pydantic import BaseModel, TypeAdapter, ValidationError, create_model
from typing_extensions import TypeVar

from chanx.core.websocket import ChanxWebsocketConsumerMixin
from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import ErrorMessage
from chanx.utils.asyncio import create_task
from chanx.utils.logging import logger

ReceiveEvent = TypeVar("ReceiveEvent", bound=BaseMessage, default=BaseMessage)

ASGIMessage = dict[str, Any]

WEBSOCKET_ACCEPT = "websocket.accept"
WEBSOCKET_CLOSE = "websocket.close"
WEBSOCKET_CONNECT = "websocket.connect"
WEBSOCKET_DISCONNECT = "websocket.disconnect"
WEBSOCKET_RECEIVE = "websocket.receive"
WEBSOCKET_SEND = "websocket.send"

DEFAULT_DISCONNECT_CODE = 1000


def _is_valid_consumer_key(key: object) -> bool:
    """
    Report whether a ``consumers`` key is usable as a wire key.

    Args:
        key: The candidate key from a ``consumers`` mapping

    Returns:
        True if the key is a non-empty string
    """
    return isinstance(key, str) and bool(key)


def _is_consumer_class(value: object) -> bool:
    """
    Report whether a ``consumers`` value is a Chanx consumer class.

    Args:
        value: The candidate value from a ``consumers`` mapping

    Returns:
        True if the value is a ChanxWebsocketConsumerMixin subclass
    """
    return isinstance(value, type) and issubclass(value, ChanxWebsocketConsumerMixin)


def is_demultiplexer(value: object) -> TypeGuard[type["ChanxDemultiplexerMixin[Any]"]]:
    """
    Report whether a value is a Chanx demultiplexer class.

    Takes a plain object because callers such as route discovery cannot always
    resolve a consumer class from an endpoint and may hold None instead.

    Args:
        value: The candidate consumer class

    Returns:
        True if the value is a ChanxDemultiplexerMixin subclass
    """
    return isinstance(value, type) and issubclass(value, ChanxDemultiplexerMixin)


def _new_asgi_queue() -> asyncio.Queue[ASGIMessage]:
    """
    Create an empty inbound ASGI message queue for a sub-consumer.

    Returns:
        A new queue of ASGI messages
    """
    return asyncio.Queue()


@dataclass
class ChildConnection:
    """
    Runtime state for a single multiplexed sub-consumer.

    Attributes:
        consumer: The sub-consumer instance driven by the demultiplexer.
        queue: Inbound ASGI message queue acting as the sub-consumer's `receive`.
        task: Task running the sub-consumer's ASGI application loop.
        closed: Whether the sub-consumer has closed and is no longer routable.
    """

    consumer: ChanxWebsocketConsumerMixin[Any]
    queue: asyncio.Queue[ASGIMessage] = field(default_factory=_new_asgi_queue)
    task: asyncio.Task[None] | None = None
    closed: bool = False


class ChanxDemultiplexerMixin(ChanxWebsocketConsumerMixin[ReceiveEvent]):
    """
    Mixin serving several Chanx consumers over a single WebSocket connection.

    The demultiplexer is itself a full Chanx consumer, so it keeps its own
    authenticator (the socket is authenticated once), groups, logging settings and
    ``@ws_handler`` methods. Frames that carry the envelope field are routed to the
    named sub-consumer; frames without it fall through to the demultiplexer's own
    handlers, which makes top-level actions such as a shared ping possible.

    Declare sub-consumers with an explicit mapping of wire key to consumer class::

        class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
            consumers = {
                "echo": EchoConsumer,
                "health": HealthConsumer,
            }

    A sub-consumer that closes the connection (for example because its own
    authenticator denied the request) is isolated: its key stops accepting
    messages, but the shared socket and every other sub-consumer keep running.
    """

    # Wire key -> sub-consumer class. Keys are arbitrary and independent of class names.
    consumers: ClassVar[dict[str, type[ChanxWebsocketConsumerMixin[Any]]]] = {}

    # Envelope field names, overridable per demultiplexer.
    envelope_consumer_field: ClassVar[str] = "consumer"
    envelope_message_field: ClassVar[str] = "message"

    # Seconds to wait for sub-consumers to shut down cleanly on disconnect.
    child_shutdown_timeout: ClassVar[float] = 5.0

    # Auto-generated envelope validator (built by __init_subclass__)
    envelope_adapter: ClassVar[TypeAdapter[BaseModel]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validate the declared sub-consumers and build the envelope validator.

        Runs the regular Chanx handler discovery first, so a demultiplexer can also
        declare its own ``@ws_handler`` and ``@event_handler`` methods.
        """
        super().__init_subclass__(**kwargs)

        if not cls.consumers:
            # Base and intermediate classes declare no sub-consumers.
            return

        cls._validate_envelope_fields()
        cls._validate_consumers()
        cls._build_envelope_adapter()

    @classmethod
    def _validate_envelope_fields(cls) -> None:
        """
        Validate the configured envelope field names.

        Raises:
            TypeError: If either field name is not a valid identifier, or if both
                       envelope fields use the same name.
        """
        for attr_name in ("envelope_consumer_field", "envelope_message_field"):
            value = getattr(cls, attr_name)
            if not isinstance(value, str) or not value.isidentifier():
                raise TypeError(
                    f"{cls.__name__}.{attr_name} must be a valid identifier,"
                    f" got {value!r}."
                )

        if cls.envelope_consumer_field == cls.envelope_message_field:
            raise TypeError(
                f"{cls.__name__} must use different names for"
                f" envelope_consumer_field and envelope_message_field,"
                f" got {cls.envelope_consumer_field!r} for both."
            )

    @classmethod
    def _validate_consumers(cls) -> None:
        """
        Validate the ``consumers`` mapping.

        Raises:
            TypeError: If a key is not a non-empty string, if a value is not a
                       Chanx consumer class, or if a value is itself a
                       demultiplexer (nesting is not supported).
        """
        for key, consumer_class in cls.consumers.items():
            if not _is_valid_consumer_key(key):
                raise TypeError(
                    f"{cls.__name__}.consumers keys must be non-empty strings,"
                    f" got {key!r}."
                )

            if not _is_consumer_class(consumer_class):
                raise TypeError(
                    f"{cls.__name__}.consumers[{key!r}] must be a Chanx consumer"
                    f" class, got {consumer_class!r}."
                )

            if issubclass(consumer_class, ChanxDemultiplexerMixin):
                raise TypeError(
                    f"{cls.__name__}.consumers[{key!r}] is a demultiplexer;"
                    f" nesting demultiplexers is not supported."
                )

    @classmethod
    def _build_envelope_adapter(cls) -> None:
        """
        Build the Pydantic validator for this demultiplexer's envelope.

        The model is generated from the configured field names so that malformed
        envelopes raise a regular ValidationError and reuse the existing
        ``handle_validation_error`` response path.
        """
        field_definitions = {
            cls.envelope_consumer_field: (str, ...),
            cls.envelope_message_field: (dict[str, Any], ...),
        }
        envelope_model = cast(
            type[BaseModel],
            create_model(f"{cls.__name__}Envelope", **field_definitions),  # type: ignore[call-overload]
        )
        cls.envelope_adapter = TypeAdapter(envelope_model)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._children: dict[str, ChildConnection] = {}
        self._child_tasks: set[asyncio.Task[Any]] = set()
        self._closed = False

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        """
        Close the shared WebSocket connection, recording that it is gone.

        The flag lets the demultiplexer skip starting sub-consumers when its own
        authentication denied the connection, and stop writing frames to a socket
        that is no longer there.

        Args:
            code: Optional WebSocket close code
            reason: Optional close reason
        """
        self._closed = True
        await super().close(code, reason)  # type: ignore[misc]

    async def websocket_connect(self, message: Any) -> None:
        """
        Accept and authenticate the shared connection, then start sub-consumers.

        Args:
            message: The connection message from the framework
        """
        await super().websocket_connect(message)

        if self._closed:
            # Authentication denied the connection; there is nothing to serve.
            return

        await self._start_children()

    async def websocket_disconnect(self, message: Any) -> None:
        """
        Shut every sub-consumer down before tearing the shared connection down.

        Sub-consumers must run their own disconnect handling so that group
        membership is discarded from the channel layer.

        Args:
            message: The disconnection message from the framework
        """
        self._closed = True
        await self._stop_children(message.get("code", DEFAULT_DISCONNECT_CODE))
        await super().websocket_disconnect(message)

    async def _start_children(self) -> None:
        """
        Instantiate every sub-consumer and run it as an ASGI application task.

        Each sub-consumer gets a private copy of the scope, a private inbound queue
        used as its `receive` callable, and a `send` wrapper that envelopes its
        outgoing frames. The scope copy is taken after authentication so values the
        authenticator added (such as ``scope["user"]``) are visible to every
        sub-consumer, while later per-sub-consumer mutations stay isolated.
        """
        for key, consumer_class in self.consumers.items():
            connection = ChildConnection(consumer=consumer_class())
            self._children[key] = connection

            child_app = cast(Any, connection.consumer)
            connection.task = create_task(
                child_app(
                    dict(self.scope),
                    connection.queue.get,
                    self._make_child_send(key),
                ),
                background_tasks=self._child_tasks,
                name=f"chanx-multiplex-{type(self).__name__}-{key}",
            )

            await connection.queue.put({"type": WEBSOCKET_CONNECT})

    async def _stop_children(self, code: int) -> None:
        """
        Ask every live sub-consumer to disconnect and wait for it to finish.

        Args:
            code: WebSocket close code to report to the sub-consumers
        """
        for connection in self._children.values():
            if not connection.closed:
                connection.closed = True
                await connection.queue.put({"type": WEBSOCKET_DISCONNECT, "code": code})

        tasks = [
            connection.task
            for connection in self._children.values()
            if connection.task is not None
        ]
        if not tasks:
            return

        _done, pending = await asyncio.wait(tasks, timeout=self.child_shutdown_timeout)
        for task in pending:
            await logger.awarning(
                "Sub-consumer did not shut down in time; cancelling",
                task_name=task.get_name(),
            )
            task.cancel()

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """
        Route an incoming frame to a sub-consumer, or to this demultiplexer.

        The envelope is read off the raw content before any decamelization, so the
        inner message reaches the sub-consumer untouched and is decamelized by that
        sub-consumer according to its own ``camelize`` setting.

        Args:
            content: The JSON content received from the client
            **kwargs: Additional keyword arguments
        """
        if self.envelope_consumer_field not in content:
            # No envelope: handle it with this demultiplexer's own handlers.
            await super().receive_json(content, **kwargs)
            return

        await self._route_to_child(content)

    async def _route_to_child(self, content: dict[str, Any]) -> None:
        """
        Validate an envelope and hand its inner message to the named sub-consumer.

        Args:
            content: The raw enveloped frame received from the client
        """
        try:
            envelope = self.envelope_adapter.validate_python(content)
        except ValidationError as e:
            await self.handle_validation_error(e)
            return

        key = cast(str, getattr(envelope, self.envelope_consumer_field))
        inner = cast(dict[str, Any], getattr(envelope, self.envelope_message_field))

        connection = self._children.get(key)
        if connection is None or connection.closed:
            await self.send_message(
                ErrorMessage(
                    payload={
                        "detail": f"Consumer '{key}' is not available",
                        self.envelope_consumer_field: key,
                    }
                )
            )
            return

        await connection.queue.put(
            {"type": WEBSOCKET_RECEIVE, "text": json.dumps(inner)}
        )

    def _make_child_send(self, key: str) -> Callable[[ASGIMessage], Awaitable[None]]:
        """
        Build the ASGI `send` callable handed to a single sub-consumer.

        Args:
            key: The wire key the sub-consumer is registered under

        Returns:
            An async callable that intercepts the sub-consumer's ASGI frames
        """

        async def child_send(message: ASGIMessage) -> None:
            """Intercept one ASGI frame produced by the sub-consumer."""
            message_type = message.get("type")

            if message_type == WEBSOCKET_ACCEPT:
                # The shared socket was already accepted by the demultiplexer.
                return

            if message_type == WEBSOCKET_CLOSE:
                await self._handle_child_close(key)
                return

            if message_type == WEBSOCKET_SEND:
                await self._send_child_frame(key, message)
                return

            await logger.awarning(
                "Ignoring unexpected frame from multiplexed consumer",
                consumer_key=key,
                frame_type=message_type,
            )

        return child_send

    async def _send_child_frame(self, key: str, message: ASGIMessage) -> None:
        """
        Envelope a sub-consumer's outgoing frame and write it to the shared socket.

        Args:
            key: The wire key the sub-consumer is registered under
            message: The ``websocket.send`` frame produced by the sub-consumer
        """
        if self._closed:
            return

        text = message.get("text")
        if text is None:
            await logger.aerror(
                "Cannot multiplex a binary frame from a consumer; dropping it",
                consumer_key=key,
            )
            return

        envelope = {
            self.envelope_consumer_field: key,
            self.envelope_message_field: json.loads(text),
        }
        await self._send_envelope(envelope)

    async def _send_envelope(self, envelope: dict[str, Any]) -> None:
        """
        Write an envelope to the shared socket.

        Deliberately bypasses :meth:`ChanxWebsocketConsumerMixin.send_json`: the
        sub-consumer has already camelized and logged the inner message under its
        own settings, so going through the Chanx layer again would emit a second,
        action-less log line for the same message.

        Args:
            envelope: The enveloped payload to serialize and send
        """
        await super(ChanxWebsocketConsumerMixin, self).send_json(envelope)  # type: ignore[misc]

        if self.send_message_immediately:
            await asyncio.sleep(0)

    async def _handle_child_close(self, key: str) -> None:
        """
        Isolate a sub-consumer that closed, keeping the shared socket alive.

        The sub-consumer is marked unroutable and told to disconnect so it still
        runs its own cleanup, and the client is told about it with an unwrapped
        error message.

        Args:
            key: The wire key the sub-consumer is registered under
        """
        connection = self._children.get(key)
        if connection is None or connection.closed:
            return

        connection.closed = True

        token = structlog.contextvars.bind_contextvars(consumer_key=key)
        await logger.ainfo("Multiplexed consumer closed")
        structlog.contextvars.reset_contextvars(**token)

        if not self._closed:
            await self.send_message(
                ErrorMessage(
                    payload={
                        "detail": f"Consumer '{key}' closed the connection",
                        self.envelope_consumer_field: key,
                    }
                )
            )

        await connection.queue.put(
            {"type": WEBSOCKET_DISCONNECT, "code": DEFAULT_DISCONNECT_CODE}
        )
