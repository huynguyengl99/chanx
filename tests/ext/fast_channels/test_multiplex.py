"""
End-to-end tests for WebSocket multiplexing over fast-channels.

Mirrors the Django Channels multiplexing tests to confirm the framework-agnostic
demultiplexer behaves identically on fast-channels: envelope routing, fall-through
to the demultiplexer's own handlers, and sub-consumers keeping their own channel
layer subscriptions.
"""

from typing import Any, ClassVar, Literal

import pytest
from chanx.core.decorators import event_handler, ws_handler
from chanx.fast_channels.multiplex import AsyncJsonWebsocketDemultiplexer
from chanx.fast_channels.testing import WebsocketCommunicator
from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from fast_channels.layers import InMemoryChannelLayer, register_channel_layer

LAYER_ALIAS = "multiplex_tests"

# Every consumer here sends completion messages so that the collecting helpers stop
# on a completion signal. A helper that instead runs out its timeout makes asgiref
# cancel the application task, which would break the rest of the test.
SEND_COMPLETION = True


@pytest.fixture(autouse=True)
def multiplex_layer() -> None:
    """Register a fresh in-memory channel layer for each test."""
    register_channel_layer(LAYER_ALIAS, InMemoryChannelLayer())


class EchoMessage(BaseMessage):
    action: Literal["fc_echo"] = "fc_echo"
    payload: str


class EchoReply(BaseMessage):
    action: Literal["fc_echo_reply"] = "fc_echo_reply"
    payload: str


class ChatMessage(BaseMessage):
    action: Literal["fc_chat"] = "fc_chat"
    payload: str


class ChatBroadcast(BaseMessage):
    action: Literal["fc_chat_broadcast"] = "fc_chat_broadcast"
    payload: str


class NotifyEvent(BaseMessage):
    action: Literal["fc_notify"] = "fc_notify"
    payload: str


class NotifyOut(BaseMessage):
    action: Literal["fc_notify_out"] = "fc_notify_out"
    payload: str


class EchoConsumer(AsyncJsonWebsocketConsumer):
    """Sub-consumer without a channel layer."""

    send_completion = SEND_COMPLETION

    @ws_handler
    async def handle_echo(self, message: EchoMessage) -> EchoReply:
        return EchoReply(payload=f"echo: {message.payload}")


class ChatConsumer(AsyncJsonWebsocketConsumer[NotifyEvent]):
    """Sub-consumer using groups and channel events on its own layer."""

    channel_layer_alias = LAYER_ALIAS
    groups = ["fc_mux_chat"]
    send_completion = SEND_COMPLETION
    disconnected: ClassVar[list[str]] = []

    @ws_handler
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @ws_handler(output_type=ChatBroadcast)
    async def handle_chat(self, message: ChatMessage) -> None:
        await self.broadcast_message(ChatBroadcast(payload=f"chat: {message.payload}"))

    @event_handler
    async def handle_notify(self, event: NotifyEvent) -> NotifyOut:
        return NotifyOut(payload=f"notified: {event.payload}")

    async def websocket_disconnect(self, message: Any) -> None:
        """Record the shutdown so tests can assert sub-consumers are torn down."""
        ChatConsumer.disconnected.append(self.channel_name)
        await super().websocket_disconnect(message)


class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    """Demultiplexer with its own top-level ping handler."""

    consumers = {"echo": EchoConsumer, "chat": ChatConsumer}
    send_completion = SEND_COMPLETION

    @ws_handler
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()


def make_communicator() -> WebsocketCommunicator:
    """Build a communicator connected straight to the demultiplexer app."""
    return WebsocketCommunicator(
        MainDemultiplexer.as_asgi(), "/mux", consumer=MainDemultiplexer
    )


async def drain(communicator: WebsocketCommunicator) -> None:
    """Round-trip a message so the chat sub-consumer has joined its group."""
    await communicator.send_message(PingMessage(), consumer="chat")
    await communicator.receive_all_envelopes(stop_consumer="chat")


@pytest.mark.asyncio
async def test_ready_frame_announces_every_consumer() -> None:
    async with make_communicator() as comm:
        ready = await comm.receive_multiplex_ready()

        assert ready.payload.version == 1
        assert sorted(ready.payload.ready) == ["chat", "echo"]
        assert ready.payload.unavailable == []


@pytest.mark.asyncio
async def test_message_is_routed_to_named_consumer() -> None:
    async with make_communicator() as comm:
        await comm.receive_multiplex_ready()
        await comm.send_message(EchoMessage(payload="hello"), consumer="echo")

        assert await comm.receive_json_from() == {
            "version": 1,
            "consumer": "echo",
            "message": EchoReply(payload="echo: hello").model_dump(),
        }


@pytest.mark.asyncio
async def test_unenveloped_message_falls_through_to_demultiplexer() -> None:
    async with make_communicator() as comm:
        await comm.receive_multiplex_ready()
        await comm.send_message(PingMessage())

        assert await comm.receive_json_from() == PongMessage().model_dump()


@pytest.mark.asyncio
async def test_unknown_consumer_key_errors_without_closing() -> None:
    async with make_communicator() as comm:
        await comm.receive_multiplex_ready()
        await comm.send_json_to({"consumer": "nope", "message": {"action": "fc_echo"}})

        response = await comm.receive_json_from()
        assert response["action"] == "error"
        assert response["payload"]["consumer"] == "nope"

        await comm.send_message(EchoMessage(payload="alive"), consumer="echo")
        assert (await comm.receive_json_from())["consumer"] == "echo"


@pytest.mark.asyncio
async def test_unsupported_envelope_version_is_rejected() -> None:
    async with make_communicator() as comm:
        await comm.receive_multiplex_ready()
        await comm.send_json_to(
            {"version": 2, "consumer": "echo", "message": {"action": "fc_echo"}}
        )

        response = await comm.receive_json_from()
        assert response["action"] == "error"
        assert response["payload"]["version"] == 1

        # The socket survives, and a versionless envelope still routes.
        await comm.send_message(EchoMessage(payload="alive"), consumer="echo")
        assert (await comm.receive_json_from())["consumer"] == "echo"


@pytest.mark.asyncio
async def test_communicator_reports_the_sending_consumer() -> None:
    async with make_communicator() as comm:
        await comm.send_message(EchoMessage(payload="one"), consumer="echo")
        await comm.send_message(PingMessage(), consumer="chat")

        envelopes = await comm.receive_all_envelopes(stop_consumer="chat")

        assert sorted(envelopes, key=lambda pair: str(pair[0])) == [
            ("chat", PongMessage()),
            ("echo", EchoReply(payload="echo: one")),
        ]


@pytest.mark.asyncio
async def test_broadcast_reaches_every_connection_enveloped() -> None:
    async with make_communicator() as first, make_communicator() as second:
        await drain(first)
        await drain(second)

        await first.send_message(ChatMessage(payload="hi all"), consumer="chat")

        expected = [("chat", ChatBroadcast(payload="chat: hi all"))]
        assert (
            await first.receive_all_envelopes(stop_action="group_complete") == expected
        )
        assert (
            await second.receive_all_envelopes(stop_action="group_complete") == expected
        )


@pytest.mark.asyncio
async def test_channel_event_reaches_the_owning_sub_consumer() -> None:
    async with make_communicator() as comm:
        await drain(comm)

        await ChatConsumer.broadcast_event(
            NotifyEvent(payload="from outside"), groups=["fc_mux_chat"]
        )

        envelopes = await comm.receive_all_envelopes(stop_action="event_complete")
        assert envelopes == [("chat", NotifyOut(payload="notified: from outside"))]


@pytest.mark.asyncio
async def test_sub_consumers_are_shut_down_on_disconnect() -> None:
    ChatConsumer.disconnected = []

    comm = make_communicator()
    await comm.connect()
    await drain(comm)
    assert ChatConsumer.disconnected == []

    await comm.disconnect()

    assert len(ChatConsumer.disconnected) == 1
