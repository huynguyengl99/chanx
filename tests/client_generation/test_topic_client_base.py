"""In-process tests for the topic client base.

The generation tests exercise these classes in a subprocess, which proves the
generated package works but leaves the base module itself unmeasured.
"""

import asyncio
from typing import Any, Literal

import pytest
from chanx.client_generator.base.topic_client import (
    BaseTopicConnection,
    BaseTopicHandle,
    ProtocolMessage,
)
from pydantic import BaseModel


class ReplyCreated(BaseModel):
    action: Literal["reply_created"] = "reply_created"
    payload: str


class Reply(BaseModel):
    action: Literal["reply"] = "reply"
    payload: str


class DiscussionHandle(BaseTopicHandle):
    pattern = "discussion:{pk}"
    incoming_message = ReplyCreated

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.received: list[Any] = []
        self.invalid: list[dict[str, Any]] = []

    async def handle_message(self, message: Any) -> None:
        self.received.append(message)

    async def handle_invalid_message(self, py_object: dict[str, Any]) -> None:
        self.invalid.append(py_object)


class Pong(BaseModel):
    action: Literal["pong"] = "pong"
    payload: None = None


class Connection(BaseTopicConnection):
    path = "/ws/hub"
    incoming_message = Pong

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.sent: list[dict[str, Any]] = []
        self.own: list[Any] = []
        self.closed = False

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)

    async def handle_message(self, message: Any) -> None:
        self.own.append(message)

    async def disconnect(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


@pytest.fixture
def connection() -> Connection:
    return Connection("localhost:8000")


def test_handle_fills_its_pattern(connection: Connection) -> None:
    handle = connection.topic(DiscussionHandle, pk=5)

    assert handle.topic == "discussion:5"
    assert connection.handles == {"discussion:5": handle}


async def test_sends_are_stamped_with_topic_and_version(
    connection: Connection,
) -> None:
    handle = connection.topic(DiscussionHandle, pk=5)

    await handle.send_message(Reply(payload="hi"))

    assert connection.sent == [
        {"action": "reply", "payload": "hi", "version": 1, "topic": "discussion:5"}
    ]


async def test_request_correlates_the_reply_by_ref(connection: Connection) -> None:
    handle = connection.topic(DiscussionHandle, pk=5)

    task = asyncio.ensure_future(handle.request(Reply(payload="hi")))
    await asyncio.sleep(0)

    (frame,) = connection.sent
    assert frame["ref"] == "1"

    await connection.dispatch_frame(
        {"action": "reply_created", "payload": "done", "ref": frame["ref"]}
    )
    reply = await task

    assert isinstance(reply, ReplyCreated)
    assert reply.payload == "done"


async def test_subscribe_and_unsubscribe_return_protocol_frames(
    connection: Connection,
) -> None:
    handle = connection.topic(DiscussionHandle, pk=5)

    for call, action in (
        (handle.subscribe, "subscribed"),
        (handle.unsubscribe, "unsubscribed"),
    ):
        task = asyncio.ensure_future(call())
        await asyncio.sleep(0)
        ref = connection.sent[-1]["ref"]
        await connection.dispatch_frame({"action": action, "payload": None, "ref": ref})
        confirmed = await task

        assert isinstance(confirmed, ProtocolMessage)
        assert confirmed.action == action


async def test_pushed_frames_route_to_their_handle(connection: Connection) -> None:
    handle = connection.topic(DiscussionHandle, pk=5)

    await connection.dispatch_frame(
        {"action": "reply_created", "payload": "pushed", "topic": "discussion:5"}
    )
    await connection.dispatch_frame(
        {"action": "not_a_topic_message", "topic": "discussion:5"}
    )
    # unknown topic: dropped, not an error
    await connection.dispatch_frame({"action": "reply_created", "topic": "nope:1"})

    assert [m.payload for m in handle.received] == ["pushed"]
    assert [f["action"] for f in handle.invalid] == ["not_a_topic_message"]


async def test_unmatched_ref_falls_through_to_topic_routing(
    connection: Connection,
) -> None:
    """A push can carry a ref from another client's request; the topic still wins."""
    handle = connection.topic(DiscussionHandle, pk=5)

    await connection.dispatch_frame(
        {
            "action": "reply_created",
            "payload": "x",
            "topic": "discussion:5",
            "ref": "99",
        }
    )

    assert [m.payload for m in handle.received] == ["x"]


async def test_frames_without_topic_belong_to_the_connection(
    connection: Connection,
) -> None:
    await connection.dispatch_frame({"action": "pong", "payload": None})

    assert [m.action for m in connection.own] == ["pong"]


async def test_request_times_out_and_forgets_the_ref(connection: Connection) -> None:
    handle = connection.topic(DiscussionHandle, pk=5)

    with pytest.raises(asyncio.TimeoutError):
        await connection.request(handle.topic, {"action": "reply"}, timeout=0.01)

    assert connection._pending == {}


async def test_resubscribe_replays_every_handle(connection: Connection) -> None:
    connection.topic(DiscussionHandle, pk=5)
    connection.topic(DiscussionHandle, pk=6)

    task = asyncio.ensure_future(connection.resubscribe())
    # answer each subscribe as it appears, so the loop can reach the next handle
    answered = 0
    for _ in range(50):
        await asyncio.sleep(0)
        if len(connection.sent) > answered:
            frame = connection.sent[answered]
            answered += 1
            await connection.dispatch_frame(
                {"action": "subscribed", "payload": None, "ref": frame["ref"]}
            )
        if task.done():
            break
    await task

    assert [(f["topic"], f["action"]) for f in connection.sent] == [
        ("discussion:5", "subscribe"),
        ("discussion:6", "subscribe"),
    ]


async def test_context_manager_disconnects(connection: Connection) -> None:
    async with connection:
        pass

    assert connection.closed is True
