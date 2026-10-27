"""join_group and leave_group at run time, driven through a real ASGI connection."""

import asyncio
from typing import Any, ClassVar, Literal

import pytest
from chanx.core.decorators import ws_handler
from chanx.fast_channels.testing import WebsocketCommunicator
from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from fastapi import FastAPI

from fast_channels.layers import InMemoryChannelLayer, register_channel_layer

LAYER_ALIAS = "groups_memory"


class JoinMessage(BaseMessage):
    action: Literal["join"] = "join"
    payload: str


class LeaveMessage(BaseMessage):
    action: Literal["leave"] = "leave"
    payload: str


class DoneMessage(BaseMessage):
    action: Literal["done"] = "done"
    payload: list[str]


class RoomEvent(BaseMessage):
    action: Literal["room_event"] = "room_event"
    payload: str


class GroupsConsumer(AsyncJsonWebsocketConsumer[RoomEvent]):
    channel_layer_alias = LAYER_ALIAS
    groups = ["lobby"]
    passthrough_events: ClassVar[list[type[BaseMessage]]] = [RoomEvent]

    @ws_handler
    async def handle_join(self, message: JoinMessage) -> DoneMessage:
        await self.join_group(message.payload)
        return DoneMessage(payload=self.groups)

    @ws_handler
    async def handle_leave(self, message: LeaveMessage) -> DoneMessage:
        await self.leave_group(message.payload)
        return DoneMessage(payload=self.groups)


app = FastAPI()
app.router.add_websocket_route("/ws/groups", GroupsConsumer.as_asgi())


class SlowAddLayer(InMemoryChannelLayer):
    """Holds group_add until released, to race it against a disconnect."""

    def __init__(self) -> None:
        super().__init__()
        self.release = asyncio.Event()
        self.adding = asyncio.Event()

    async def group_add(self, group: str, channel: str) -> None:
        if group == "slow":
            self.adding.set()
            await self.release.wait()
        await super().group_add(group, channel)


@pytest.fixture
def layer() -> InMemoryChannelLayer:
    layer = InMemoryChannelLayer()
    register_channel_layer(LAYER_ALIAS, layer)
    return layer


def _members(layer: InMemoryChannelLayer, group: str) -> dict[str, Any]:
    return layer.groups.get(group, {})


@pytest.mark.asyncio
@pytest.mark.usefixtures("layer")
async def test_joined_group_receives_broadcasts() -> None:
    async with WebsocketCommunicator(
        app, "/ws/groups", consumer=GroupsConsumer
    ) as comm:
        await comm.send_message(JoinMessage(payload="room_1"))
        reply = await comm.receive_json_from(timeout=2)
        assert reply["payload"] == ["lobby", "room_1"]

        await GroupsConsumer.broadcast_event(RoomEvent(payload="hi"), "room_1")
        pushed = await comm.receive_json_from(timeout=2)
        assert pushed == {"action": "room_event", "payload": "hi"}


@pytest.mark.asyncio
@pytest.mark.usefixtures("layer")
async def test_joining_twice_lists_the_group_once() -> None:
    async with WebsocketCommunicator(
        app, "/ws/groups", consumer=GroupsConsumer
    ) as comm:
        await comm.send_message(JoinMessage(payload="lobby"))
        reply = await comm.receive_json_from(timeout=2)
        assert reply["payload"] == ["lobby"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("layer")
async def test_left_group_no_longer_receives() -> None:
    async with WebsocketCommunicator(
        app, "/ws/groups", consumer=GroupsConsumer
    ) as comm:
        await comm.send_message(LeaveMessage(payload="lobby"))
        reply = await comm.receive_json_from(timeout=2)
        assert reply["payload"] == []

        await GroupsConsumer.broadcast_event(RoomEvent(payload="gone"), "lobby")
        assert await comm.receive_nothing(timeout=0.3)


@pytest.mark.asyncio
async def test_disconnect_leaves_a_joined_group(layer: InMemoryChannelLayer) -> None:
    async with WebsocketCommunicator(
        app, "/ws/groups", consumer=GroupsConsumer
    ) as comm:
        await comm.send_message(JoinMessage(payload="room_1"))
        await comm.receive_json_from(timeout=2)
        assert _members(layer, "room_1")

    assert not _members(layer, "room_1")
    assert not _members(layer, "lobby")


@pytest.mark.asyncio
async def test_join_racing_a_disconnect_is_undone() -> None:
    layer = SlowAddLayer()
    register_channel_layer(LAYER_ALIAS, layer)

    async with WebsocketCommunicator(
        app, "/ws/groups", consumer=GroupsConsumer
    ) as comm:
        await comm.send_message(JoinMessage(payload="slow"))
        await asyncio.wait_for(layer.adding.wait(), timeout=2)

    layer.release.set()
    await asyncio.sleep(0.05)
    assert not _members(layer, "slow")
