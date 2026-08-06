"""Two logical consumers composed onto one path, exercised over a single connection."""

from typing import ClassVar, Literal

import pytest
from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.core.decorators import event_handler, ws_handler
from chanx.fast_channels.testing import WebsocketCommunicator
from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from fastapi import FastAPI

from fast_channels.layers import InMemoryChannelLayer, register_channel_layer

LAYER_ALIAS = "mux_memory"


class HealthReq(BaseMessage):
    action: Literal["mux_health"] = "mux_health"
    payload: None = None


class HealthRes(BaseMessage):
    action: Literal["mux_health_res"] = "mux_health_res"
    payload: str


class HealthAlertEvent(BaseMessage):
    action: Literal["mux_health_alert"] = "mux_health_alert"
    payload: str


class HealthMixin:
    extra_groups: ClassVar[list[str]] = ["mux_health_group"]
    passthrough_events: ClassVar[list[type[BaseMessage]]] = [HealthAlertEvent]

    @ws_handler
    async def handle_health(self, _message: HealthReq) -> HealthRes:
        return HealthRes(payload="ok!")


class EchoReq(BaseMessage):
    action: Literal["mux_echo"] = "mux_echo"
    payload: str


class EchoRes(BaseMessage):
    action: Literal["mux_echo_res"] = "mux_echo_res"
    payload: str


class EchoTickEvent(BaseMessage):
    action: Literal["mux_echo_tick"] = "mux_echo_tick"
    payload: str


class EchoRelayMessage(BaseMessage):
    action: Literal["mux_echo_relay"] = "mux_echo_relay"
    payload: str


class EchoMixin:
    extra_groups: ClassVar[list[str]] = ["mux_echo_group"]

    @ws_handler
    async def handle_echo(self, message: EchoReq) -> EchoRes:
        return EchoRes(payload=message.payload)

    @event_handler
    async def handle_echo_tick(self, event: EchoTickEvent) -> EchoRelayMessage:
        return EchoRelayMessage(payload=f"tick:{event.payload}")


AllEvent = HealthAlertEvent | EchoTickEvent


class GatewayConsumer(HealthMixin, EchoMixin, AsyncJsonWebsocketConsumer[AllEvent]):  # type: ignore[misc]
    channel_layer_alias = LAYER_ALIAS
    send_completion = True


app = FastAPI()
app.add_websocket_route("/ws/gateway", GatewayConsumer.as_asgi())


@pytest.fixture(autouse=True)
def memory_layer() -> None:
    register_channel_layer(LAYER_ALIAS, InMemoryChannelLayer())


@pytest.mark.asyncio
async def test_both_halves_route_over_one_connection() -> None:
    async with WebsocketCommunicator(
        app, "/ws/gateway", consumer=GatewayConsumer
    ) as comm:
        await comm.send_message(HealthReq())
        assert await comm.receive_all_messages() == [HealthRes(payload="ok!")]

        await comm.send_message(EchoReq(payload="hi"))
        assert await comm.receive_all_messages() == [EchoRes(payload="hi")]


@pytest.mark.asyncio
async def test_both_halves_receive_their_own_group_events() -> None:
    """Each mixin's extra_groups is joined, so neither half's events are dropped."""
    async with WebsocketCommunicator(
        app, "/ws/gateway", consumer=GatewayConsumer
    ) as comm:
        await GatewayConsumer.broadcast_event(
            HealthAlertEvent(payload="cpu high"), groups=["mux_health_group"]
        )
        assert await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE) == [
            HealthAlertEvent(payload="cpu high")
        ]

        await GatewayConsumer.broadcast_event(
            EchoTickEvent(payload="42"), groups=["mux_echo_group"]
        )
        assert await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE) == [
            EchoRelayMessage(payload="tick:42")
        ]
