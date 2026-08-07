"""Tests for the generated client runtime of a multiplexed route."""

import json
from typing import Any, Literal

import pytest
from chanx.client_generator.base.demultiplexer import (
    BaseDemultiplexerClient,
    BaseSubClient,
    StreamUnavailableError,
)
from pydantic import BaseModel


class EchoMessage(BaseModel):
    action: Literal["echo"] = "echo"
    payload: str


class ChatMessage(BaseModel):
    action: Literal["chat"] = "chat"
    payload: str


class PongMessage(BaseModel):
    action: Literal["pong"] = "pong"
    payload: None = None


class EchoSubClient(BaseSubClient):
    consumer_key = "echo"
    incoming_message = EchoMessage

    def __init__(self, parent: BaseDemultiplexerClient):
        super().__init__(parent)
        self.received: list[Any] = []
        self.invalid: list[Any] = []

    async def handle_message(self, message: Any) -> None:
        self.received.append(message)

    async def handle_invalid_message(self, invalid_message: Any) -> None:
        self.invalid.append(invalid_message)


class ChatSubClient(BaseSubClient):
    consumer_key = "chat"
    incoming_message = ChatMessage

    def __init__(self, parent: BaseDemultiplexerClient):
        super().__init__(parent)
        self.received: list[Any] = []

    async def handle_message(self, message: Any) -> None:
        self.received.append(message)


class RecordingClient(BaseDemultiplexerClient):
    """Demultiplexer client that records instead of touching a socket."""

    path = "/ws/mux"
    incoming_message = PongMessage
    sub_client_classes = {"echo": EchoSubClient, "chat": ChatSubClient}

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.sent: list[dict[str, Any]] = []
        self.own_messages: list[Any] = []
        self.invalid: list[Any] = []
        self.ready_calls: list[tuple[list[str], list[str]]] = []
        self.gone: list[str] = []

    async def send_raw(self, data: str | bytes) -> None:
        self.sent.append(json.loads(data))

    async def handle_message(self, message: Any) -> None:
        self.own_messages.append(message)

    async def handle_invalid_message(self, invalid_message: Any) -> None:
        self.invalid.append(invalid_message)

    async def on_ready(self, ready: list[str], unavailable: list[str]) -> None:
        self.ready_calls.append((ready, unavailable))

    async def on_stream_unavailable(self, consumer: str) -> None:
        self.gone.append(consumer)


@pytest.fixture
def client() -> RecordingClient:
    return RecordingClient("localhost:8000")


class TestOutgoing:
    @pytest.mark.asyncio
    async def test_addressed_message_is_enveloped(
        self, client: RecordingClient
    ) -> None:
        await client.send_message(EchoMessage(payload="hi"), consumer="echo")

        assert client.sent == [
            {
                "version": 1,
                "consumer": "echo",
                "message": {"action": "echo", "payload": "hi"},
            }
        ]

    @pytest.mark.asyncio
    async def test_sub_client_addresses_its_own_key(
        self, client: RecordingClient
    ) -> None:
        await client.consumers["chat"].send_message(ChatMessage(payload="hi"))

        assert client.sent[0]["consumer"] == "chat"

    @pytest.mark.asyncio
    async def test_unaddressed_message_is_sent_unwrapped(
        self, client: RecordingClient
    ) -> None:
        await client.send_message(PongMessage())

        assert client.sent == [{"action": "pong", "payload": None}]

    @pytest.mark.asyncio
    async def test_unknown_consumer_is_refused_locally(
        self, client: RecordingClient
    ) -> None:
        with pytest.raises(StreamUnavailableError, match="Unknown consumer"):
            await client.send_message(EchoMessage(payload="hi"), consumer="nope")

        assert client.sent == []

    @pytest.mark.asyncio
    async def test_unavailable_consumer_is_refused_locally(
        self, client: RecordingClient
    ) -> None:
        """A dead stream fails at the client rather than round-tripping."""
        await client.dispatch(
            {
                "action": "multiplex_ready",
                "payload": {"version": 1, "ready": ["chat"], "unavailable": ["echo"]},
            }
        )

        with pytest.raises(StreamUnavailableError, match="unavailable"):
            await client.send_message(EchoMessage(payload="hi"), consumer="echo")


class TestIncoming:
    @pytest.mark.asyncio
    async def test_enveloped_frame_reaches_its_sub_client(
        self, client: RecordingClient
    ) -> None:
        await client.dispatch(
            {
                "version": 1,
                "consumer": "echo",
                "message": {"action": "echo", "payload": "hi"},
            }
        )

        assert client.consumers["echo"].received == [EchoMessage(payload="hi")]  # type: ignore[attr-defined]
        assert client.consumers["chat"].received == []  # type: ignore[attr-defined]
        assert client.own_messages == []

    @pytest.mark.asyncio
    async def test_unwrapped_frame_reaches_the_demultiplexer(
        self, client: RecordingClient
    ) -> None:
        await client.dispatch({"action": "pong", "payload": None})

        assert client.own_messages == [PongMessage()]

    @pytest.mark.asyncio
    async def test_inner_message_failing_validation_is_reported(
        self, client: RecordingClient
    ) -> None:
        await client.dispatch(
            {"consumer": "echo", "message": {"action": "echo", "payload": 5}}
        )

        assert client.consumers["echo"].invalid == [{"action": "echo", "payload": 5}]  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_frame_for_an_ungenerated_consumer_is_reported(
        self, client: RecordingClient
    ) -> None:
        frame = {"consumer": "admin", "message": {"action": "echo", "payload": "hi"}}

        await client.dispatch(frame)

        assert client.invalid == [frame]


class TestProtocolFrames:
    @pytest.mark.asyncio
    async def test_handshake_reaches_on_ready(self, client: RecordingClient) -> None:
        await client.dispatch(
            {
                "action": "multiplex_ready",
                "payload": {"version": 1, "ready": ["echo"], "unavailable": ["chat"]},
            }
        )

        assert client.ready_calls == [(["echo"], ["chat"])]
        assert client.unavailable == {"chat"}
        # Consumed as protocol, not forwarded as a message.
        assert client.own_messages == []

    @pytest.mark.asyncio
    async def test_error_naming_a_consumer_closes_that_stream(
        self, client: RecordingClient
    ) -> None:
        await client.dispatch(
            {
                "action": "error",
                "payload": {
                    "detail": "Consumer 'chat' closed the connection",
                    "consumer": "chat",
                },
            }
        )

        assert client.gone == ["chat"]
        assert client.unavailable == {"chat"}

    @pytest.mark.asyncio
    async def test_a_stream_is_only_reported_gone_once(
        self, client: RecordingClient
    ) -> None:
        error = {
            "action": "error",
            "payload": {
                "detail": "Consumer 'chat' is not available",
                "consumer": "chat",
            },
        }

        await client.dispatch(error)
        await client.dispatch(error)

        assert client.gone == ["chat"]

    @pytest.mark.asyncio
    async def test_error_without_a_consumer_leaves_streams_alone(
        self, client: RecordingClient
    ) -> None:
        await client.dispatch(
            {"action": "error", "payload": {"detail": "Unsupported envelope version 2"}}
        )

        assert client.gone == []
        assert client.unavailable == set()
