"""Topics in the sandbox: one connection, several streams."""

import pytest
from chanx.fast_channels.testing import WebsocketCommunicator

from sandbox_fastapi.apps.topics.consumer import (
    RoomTopic,
    RoomTopicConsumer,
    TopicHubConsumer,
)
from sandbox_fastapi.apps.topics.messages import PostPayload, RoomEvent
from sandbox_fastapi.main import app


@pytest.mark.asyncio
async def test_two_topics_over_one_connection() -> None:
    async with WebsocketCommunicator(
        app, "/ws/topics", consumer=TopicHubConsumer
    ) as comm:
        await comm.send_json_to(
            {"topic": "room:lobby", "ref": "1", "action": "subscribe"}
        )
        assert (await comm.receive_json_from(timeout=2))["action"] == "subscribed"

        await comm.send_json_to(
            {"topic": "presence:alice", "ref": "2", "action": "subscribe"}
        )
        assert (await comm.receive_json_from(timeout=2))["action"] == "subscribed"

        await comm.send_json_to(
            {
                "topic": "room:lobby",
                "ref": "3",
                "action": "echo",
                "payload": {"body": "hi", "author": "alice"},
            }
        )
        reply = await comm.receive_json_from(timeout=2)
        assert reply["action"] == "posted"
        assert reply["topic"] == "room:lobby"
        assert reply["ref"] == "3"


@pytest.mark.asyncio
async def test_broadcast_reaches_the_subscribed_topic() -> None:
    async with WebsocketCommunicator(
        app, "/ws/topics", consumer=TopicHubConsumer
    ) as comm:
        await comm.send_json_to(
            {"topic": "room:lobby", "ref": "1", "action": "subscribe"}
        )
        await comm.receive_json_from(timeout=2)

        await RoomTopic.broadcast(
            "room:lobby", RoomEvent(payload=PostPayload(body="hello")), seq=7
        )

        pushed = await comm.receive_json_from(timeout=2)
        assert pushed["action"] == "room_event"
        assert pushed["topic"] == "room:lobby"
        assert pushed["seq"] == 7


@pytest.mark.asyncio
async def test_same_topic_on_its_own_route_shares_the_group() -> None:
    """A client on the dedicated route sends no envelope but joins the same group."""
    async with WebsocketCommunicator(
        app, "/ws/topics/room/lobby", consumer=RoomTopicConsumer
    ) as comm:
        assert (await comm.receive_json_from(timeout=2))["action"] == "subscribed"

        await RoomTopic.broadcast(
            "room:lobby", RoomEvent(payload=PostPayload(body="from the hub"))
        )

        pushed = await comm.receive_json_from(timeout=2)
        assert pushed["action"] == "room_event"
        assert pushed["payload"]["body"] == "from the hub"
