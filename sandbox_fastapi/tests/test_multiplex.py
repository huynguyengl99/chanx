from typing import Any

import pytest
from chanx.fast_channels.testing import WebsocketCommunicator
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from sandbox_fastapi.apps.multiplex.consumer import MainDemultiplexer
from sandbox_fastapi.apps.showcase.consumer import ChatConsumer
from sandbox_fastapi.apps.showcase.messages import (
    ChatMessage,
    ChatNotificationMessage,
    ChatPayload,
)
from sandbox_fastapi.apps.system_chat.messages import (
    MessagePayload,
    SystemEchoMessage,
    UserMessage,
)
from sandbox_fastapi.main import app


def make_communicator() -> WebsocketCommunicator:
    """Connect to the multiplexed route."""
    return WebsocketCommunicator(app, "/ws/mux", consumer=MainDemultiplexer)


async def drain(comm: WebsocketCommunicator, quiet: float = 0.4) -> list[Any]:
    """
    Collect frames until the socket has been quiet for a moment.

    Uses receive_nothing() rather than receive_all_json(): a collector that ends by
    timing out makes asgiref cancel the application task, which would take the
    connection down mid-test. Every sub-consumer greets on connect, and the chat and
    notification greetings travel through Redis, so the opening burst has to be
    drained before a test can assert on anything it sends itself.
    """
    frames: list[Any] = []
    while not await comm.receive_nothing(timeout=quiet, interval=0.02):
        frames.append(await comm.receive_json_from())
    return frames


@pytest.mark.asyncio
async def test_every_sub_consumer_greets_under_its_own_key() -> None:
    async with make_communicator() as comm:
        greetings = await drain(comm)

        keyed = {
            frame["consumer"]: frame["message"]
            for frame in greetings
            if "consumer" in frame
        }
        assert (
            keyed["system"]
            == SystemEchoMessage(
                payload=MessagePayload(message="🔧 System: Connection established!")
            ).model_dump()
        )
        assert {"system", "chat", "notifications"} <= set(keyed)


@pytest.mark.asyncio
async def test_sub_consumers_are_independently_addressable() -> None:
    async with make_communicator() as comm:
        await drain(comm)

        await comm.send_message(PingMessage(), consumer="system")
        assert await comm.receive_all_envelopes(stop_consumer="system") == [
            ("system", PongMessage())
        ]

        message = "This is a multiplexed message"
        await comm.send_message(
            UserMessage(payload=MessagePayload(message=message)), consumer="system"
        )
        assert await comm.receive_all_envelopes(stop_consumer="system") == [
            (
                "system",
                SystemEchoMessage(
                    payload=MessagePayload(message=f"🔧 System Echo: {message}")
                ),
            )
        ]


@pytest.mark.asyncio
async def test_unenveloped_message_reaches_the_demultiplexer() -> None:
    async with make_communicator() as comm:
        await drain(comm)

        await comm.send_message(PingMessage())

        assert await comm.receive_all_envelopes() == [(None, PongMessage())]


@pytest.mark.asyncio
async def test_unknown_consumer_key_is_reported_unwrapped() -> None:
    async with make_communicator() as comm:
        await drain(comm)

        await comm.send_json_to({"consumer": "nope", "message": {"action": "ping"}})

        response = await comm.receive_json_from()
        assert response["action"] == "error"
        assert response["payload"]["consumer"] == "nope"

        # The shared connection survives.
        await comm.send_message(PingMessage(), consumer="system")
        assert await comm.receive_all_envelopes(stop_consumer="system") == [
            ("system", PongMessage())
        ]


@pytest.mark.asyncio
async def test_multiplexed_sub_consumer_keeps_its_channel_layer() -> None:
    """A multiplexed chat consumer stays in the same group as the dedicated route."""
    async with (
        make_communicator() as muxed,
        WebsocketCommunicator(app, "/ws/chat", consumer=ChatConsumer) as direct,
    ):
        await drain(muxed)
        await drain(direct)

        await muxed.send_message(
            ChatMessage(payload=ChatPayload(message="hello from the mux")),
            consumer="chat",
        )

        expected = ChatNotificationMessage(
            payload=ChatPayload(message="💬 hello from the mux")
        ).model_dump()

        # Enveloped on the multiplexed route...
        on_mux = await drain(muxed)
        assert {"consumer": "chat", "message": expected} in on_mux

        # ...and plain on the consumer's own route.
        assert expected in await drain(direct)
