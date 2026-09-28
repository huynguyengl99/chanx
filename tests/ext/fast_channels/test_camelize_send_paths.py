"""Camelization applies to every send path, not just direct sends."""

from typing import ClassVar, Literal

import pytest
from chanx.core.decorators import ws_handler
from chanx.fast_channels.testing import WebsocketCommunicator
from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from fastapi import FastAPI
from pydantic import BaseModel

from fast_channels.layers import InMemoryChannelLayer, register_channel_layer

LAYER_ALIAS = "camel_paths_memory"
GROUP = "camel_paths_group"

register_channel_layer(LAYER_ALIAS, InMemoryChannelLayer())


class EventPayload(BaseModel):
    event_type: str
    created_at: str


class HowReq(BaseMessage):
    action: Literal["how"] = "how"
    payload: str


class EventRes(BaseMessage):
    action: Literal["event_res"] = "event_res"
    payload: EventPayload


SAMPLE = EventRes(
    payload=EventPayload(event_type="comment", created_at="2026-01-01T00:00:00Z")
)


class CamelPathsConsumer(AsyncJsonWebsocketConsumer[BaseMessage]):
    camelize = True
    channel_layer_alias = LAYER_ALIAS
    groups: ClassVar[list[str]] = [GROUP]

    @ws_handler(output_type=EventRes)
    async def handle_how(self, message: HowReq) -> None:
        if message.payload == "direct":
            await self.send_message(SAMPLE)
        else:
            await self.broadcast_message(SAMPLE)


app = FastAPI()
app.router.add_websocket_route("/ws/camel-paths", CamelPathsConsumer.as_asgi())


async def _payload_keys(how: str) -> list[str]:
    async with WebsocketCommunicator(
        app, "/ws/camel-paths", consumer=CamelPathsConsumer
    ) as comm:
        await comm.send_json_to({"action": "how", "payload": how})
        for _ in range(5):
            frame = await comm.receive_json_from()
            if frame.get("action") == "event_res":
                return sorted(frame["payload"])
    raise AssertionError("no event_res frame arrived")


@pytest.mark.asyncio
async def test_direct_send_camelizes() -> None:
    assert await _payload_keys("direct") == ["createdAt", "eventType"]


@pytest.mark.asyncio
async def test_group_broadcast_camelizes_too() -> None:
    assert await _payload_keys("broadcast") == ["createdAt", "eventType"]
