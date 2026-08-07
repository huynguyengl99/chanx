"""Base WebSocket client for a multiplexed AsyncAPI route."""

from types import UnionType
from typing import Annotated, Any

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from .client import BaseClient

MULTIPLEX_READY_ACTION = "multiplex_ready"
ERROR_ACTION = "error"


class StreamUnavailableError(RuntimeError):
    """Raised when a message is addressed to a consumer that is not usable."""


class BaseSubClient:
    """
    One multiplexed consumer, seen from the client side.

    A sub-client owns no socket: it borrows the demultiplexer client's, and its
    envelope key is added on the way out and stripped on the way in. Subclassing
    it is the same job as subclassing a single-channel client -- override
    handle_message, call send_message.
    """

    consumer_key: str
    incoming_message: type[BaseModel] | UnionType
    discriminator_field: str = "action"

    def __init__(self, parent: "BaseDemultiplexerClient"):
        """
        Args:
            parent: The demultiplexer client owning the shared connection
        """
        self.parent = parent
        self.incoming_message_adapter = TypeAdapter[BaseModel](
            Annotated[
                self.incoming_message,
                Field(discriminator=self.discriminator_field),
            ]
        )

    async def send_message(self, message: Any) -> None:
        """
        Send a message to this consumer.

        Args:
            message: Pydantic model instance to send, enveloped under this
                     sub-client's key
        """
        await self.parent.send_message(message, consumer=self.consumer_key)

    async def dispatch(self, inner: Any) -> None:
        """
        Validate one unwrapped message and route it to this sub-client's handler.

        Args:
            inner: The inner message lifted out of the envelope
        """
        try:
            message = self.incoming_message_adapter.validate_python(inner)
        except ValidationError:
            await self.handle_invalid_message(inner)
            return

        await self.handle_message(message)

    async def handle_message(self, message: Any) -> None:
        """
        Handle a message from this consumer.

        Override this method in subclasses. In generated sub-clients the parameter
        is narrowed to that consumer's union of incoming messages.

        Args:
            message: Validated Pydantic message model received from the server
        """
        pass

    async def handle_invalid_message(self, invalid_message: Any) -> None:
        """
        Handle a message from this consumer that failed validation.

        Args:
            invalid_message: The parsed JSON object that failed validation
        """
        await self.parent.handle_invalid_message(invalid_message)


class BaseDemultiplexerClient(BaseClient):
    """
    Client for a route that serves several consumers over one connection.

    Owns the socket and the envelope. Frames addressed to a consumer are handed to
    that sub-client; frames without an envelope are the demultiplexer's own and are
    handled here, exactly mirroring the server side.

    The two protocol frames are turned into hooks rather than messages: on_ready()
    when the route reports which consumers are addressable, and
    on_stream_unavailable() when one of them turns out not to be. Overriding them
    is how a client implements the reconnect and resubscription rules from the
    multiplexing protocol specification.
    """

    consumer_field: str = "consumer"
    message_field: str = "message"
    version_field: str = "version"
    envelope_version: int = 1

    # Envelope key -> sub-client class, filled in by the generated subclass.
    sub_client_classes: dict[str, type[BaseSubClient]] = {}

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.consumers: dict[str, BaseSubClient] = {
            key: sub_client_class(self)
            for key, sub_client_class in self.sub_client_classes.items()
        }
        self.unavailable: set[str] = set()

    async def send_message(self, message: Any, *, consumer: str | None = None) -> None:
        """
        Send a message, optionally addressed to one multiplexed consumer.

        Args:
            message: Pydantic model instance to send
            consumer: Envelope key to address. Omit to reach the demultiplexer's
                      own handlers, which is what un-enveloped frames mean.

        Raises:
            StreamUnavailableError: If the consumer is unknown to this client, or
                                    the server reported it unavailable. A stream
                                    stays unavailable for the life of the
                                    connection, so retrying cannot help.
        """
        if consumer is None:
            await self.send_json(message.model_dump())
            return

        if consumer not in self.consumers:
            raise StreamUnavailableError(f"Unknown consumer {consumer!r}")
        if consumer in self.unavailable:
            raise StreamUnavailableError(
                f"Consumer {consumer!r} is unavailable on this connection"
            )

        await self.send_json(
            {
                self.version_field: self.envelope_version,
                self.consumer_field: consumer,
                self.message_field: message.model_dump(),
            }
        )

    async def dispatch(self, py_object: Any) -> None:
        """
        Unwrap one frame and route it to a sub-client or to this client.

        Args:
            py_object: The decoded JSON frame received from the server
        """
        key = (
            py_object.get(self.consumer_field) if isinstance(py_object, dict) else None
        )

        if key is None:
            await self._dispatch_unwrapped(py_object)
            return

        sub_client = self.consumers.get(key)
        if sub_client is None:
            await self.handle_unknown_consumer(key, py_object)
            return

        await sub_client.dispatch(py_object.get(self.message_field) or {})

    async def _dispatch_unwrapped(self, py_object: Any) -> None:
        """
        Handle a frame the demultiplexer sent on its own behalf.

        The two protocol frames are consumed here rather than forwarded: the
        handshake becomes on_ready(), and an error naming a consumer marks that
        stream dead before reaching the user's error handling.

        Args:
            py_object: The decoded, un-enveloped JSON frame
        """
        action = py_object.get(self.discriminator_field)

        if action == MULTIPLEX_READY_ACTION:
            payload = py_object.get("payload") or {}
            ready = list(payload.get("ready") or [])
            unavailable = list(payload.get("unavailable") or [])
            self.unavailable.update(unavailable)
            await self.on_ready(ready, unavailable)
            return

        if action == ERROR_ACTION:
            key = (py_object.get("payload") or {}).get(self.consumer_field)
            if key in self.consumers and key not in self.unavailable:
                self.unavailable.add(key)
                await self.on_stream_unavailable(key)

        await super().dispatch(py_object)

    async def on_ready(self, ready: list[str], unavailable: list[str]) -> None:
        """
        Handle the handshake announcing which consumers are addressable.

        Sent once per connection, after every consumer has connected. This is the
        point at which group traffic is guaranteed to reach them, and the place to
        replay per-key subscriptions -- on a first connection and on a reconnect
        alike, since a reconnect keeps no client-established state.

        Args:
            ready: Envelope keys that are connected and accepting messages
            unavailable: Envelope keys that failed to connect
        """
        pass

    async def on_stream_unavailable(self, consumer: str) -> None:
        """
        Handle one consumer becoming unusable, without losing the connection.

        Most often its own authenticator denied the request. The stream cannot be
        reopened on this connection; only a new connection can bring it back.

        Args:
            consumer: The envelope key that is no longer addressable
        """
        pass

    async def handle_unknown_consumer(self, consumer: str, py_object: Any) -> None:
        """
        Handle an enveloped frame naming a consumer this client does not generate.

        Reached when the server serves more consumers than the schema the client
        was generated from; regenerating the client is the fix.

        Args:
            consumer: The envelope key the server used
            py_object: The full enveloped frame
        """
        await self.handle_invalid_message(py_object)
