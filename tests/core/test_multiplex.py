"""
Tests for chanx.core.multiplex module.

Covers the framework-agnostic parts of the demultiplexer: subclass validation,
envelope adapter construction, and expansion of a multiplexed route into one
route per sub-consumer.
"""

from typing import Any, Literal

import pytest
from chanx.channels.multiplex import AsyncJsonWebsocketDemultiplexer
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.decorators import ws_handler
from chanx.core.multiplex import ChanxDemultiplexerMixin, is_demultiplexer
from chanx.messages.base import BaseMessage
from chanx.routing.discovery import RouteInfo, expand_multiplexed_route
from pydantic import ValidationError


class EchoMessage(BaseMessage):
    action: Literal["mux_echo"] = "mux_echo"
    payload: str


class EchoReply(BaseMessage):
    action: Literal["mux_echo_reply"] = "mux_echo_reply"
    payload: str


class HealthMessage(BaseMessage):
    action: Literal["mux_health"] = "mux_health"
    payload: None = None


class HealthReply(BaseMessage):
    action: Literal["mux_health_reply"] = "mux_health_reply"
    payload: str


class EchoConsumer(AsyncJsonWebsocketConsumer):
    @ws_handler
    async def handle_echo(self, message: EchoMessage) -> EchoReply:
        return EchoReply(payload=message.payload)


class HealthConsumer(AsyncJsonWebsocketConsumer):
    @ws_handler
    async def handle_health(self, _message: HealthMessage) -> HealthReply:
        return HealthReply(payload="ok")


class PlainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    consumers = {"echo": EchoConsumer, "health": HealthConsumer}


class HandlerDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    consumers = {"echo": EchoConsumer}

    @ws_handler
    async def handle_health(self, _message: HealthMessage) -> HealthReply:
        return HealthReply(payload="demultiplexer")


def make_route(consumer: Any, path: str = "ws/mux/") -> RouteInfo:
    """Build a RouteInfo for the given consumer class."""
    return RouteInfo(
        path=path,
        handler=object(),
        base_url="ws://localhost:8000",
        consumer=consumer,
    )


def declare_demultiplexer(**namespace: Any) -> type[Any]:
    """
    Declare a demultiplexer subclass, running its class-creation validation.

    Args:
        **namespace: Class attributes for the new demultiplexer

    Returns:
        The newly created demultiplexer class
    """
    return type("Declared", (AsyncJsonWebsocketDemultiplexer,), namespace)


class TestDeclarationValidation:
    """Test validation of a demultiplexer declaration at class-creation time."""

    def test_valid_consumers_are_accepted(self) -> None:
        assert PlainDemultiplexer.consumers == {
            "echo": EchoConsumer,
            "health": HealthConsumer,
        }

    def test_empty_consumers_is_allowed(self) -> None:
        """Base and intermediate classes may declare no sub-consumers."""
        assert declare_demultiplexer().consumers == {}

    def test_custom_envelope_field_names_are_accepted(self) -> None:
        declared = declare_demultiplexer(
            consumers={"echo": EchoConsumer},
            envelope_consumer_field="stream",
            envelope_message_field="data",
        )

        assert declared.envelope_consumer_field == "stream"
        assert declared.envelope_message_field == "data"

    @pytest.mark.parametrize(
        "namespace, match",
        [
            pytest.param(
                {"consumers": {"": EchoConsumer}},
                "non-empty strings",
                id="empty-key",
            ),
            pytest.param(
                {"consumers": {1: EchoConsumer}},
                "non-empty strings",
                id="non-string-key",
            ),
            pytest.param(
                {"consumers": {"echo": str}},
                "must be a Chanx consumer class",
                id="not-a-consumer",
            ),
            pytest.param(
                {"consumers": {"inner": PlainDemultiplexer}},
                "nesting demultiplexers is not supported",
                id="nested-demultiplexer",
            ),
            pytest.param(
                {
                    "consumers": {"echo": EchoConsumer},
                    "envelope_consumer_field": "stream",
                    "envelope_message_field": "stream",
                },
                "must use different names",
                id="identical-envelope-fields",
            ),
            pytest.param(
                {
                    "consumers": {"echo": EchoConsumer},
                    "envelope_consumer_field": "not an identifier",
                },
                "must be a valid identifier",
                id="non-identifier-envelope-field",
            ),
        ],
    )
    def test_invalid_declaration_is_rejected(
        self, namespace: dict[str, Any], match: str
    ) -> None:
        with pytest.raises(TypeError, match=match):
            declare_demultiplexer(**namespace)


class TestEnvelopeAdapter:
    """Test the auto-generated envelope validator."""

    def test_valid_envelope_validates(self) -> None:
        envelope = PlainDemultiplexer.envelope_adapter.validate_python(
            {"consumer": "echo", "message": {"action": "mux_echo", "payload": "hi"}}
        )
        assert envelope.consumer == "echo"  # type: ignore[attr-defined]
        assert envelope.message == {"action": "mux_echo", "payload": "hi"}  # type: ignore[attr-defined]

    def test_adapter_uses_custom_field_names(self) -> None:
        declared = declare_demultiplexer(
            consumers={"echo": EchoConsumer},
            envelope_consumer_field="stream",
            envelope_message_field="data",
        )

        envelope = declared.envelope_adapter.validate_python(
            {"stream": "echo", "data": {"action": "mux_echo", "payload": "hi"}}
        )
        assert envelope.stream == "echo"

    @pytest.mark.parametrize(
        "content",
        [
            {"consumer": "echo"},
            {"message": {"action": "mux_echo"}},
            {"consumer": "echo", "message": "not-a-dict"},
            {"consumer": 5, "message": {}},
        ],
    )
    def test_malformed_envelope_is_rejected(self, content: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            PlainDemultiplexer.envelope_adapter.validate_python(content)

    def test_each_demultiplexer_gets_its_own_adapter(self) -> None:
        assert (
            PlainDemultiplexer.envelope_adapter
            is not HandlerDemultiplexer.envelope_adapter
        )


class TestIsDemultiplexer:
    """Test the demultiplexer type guard."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (PlainDemultiplexer, True),
            (ChanxDemultiplexerMixin, True),
            (EchoConsumer, False),
            (None, False),
            ("echo", False),
            (PlainDemultiplexer(), False),
        ],
    )
    def test_is_demultiplexer(self, value: Any, expected: bool) -> None:
        assert is_demultiplexer(value) is expected


class TestExpandMultiplexedRoute:
    """Test expansion of a discovered route into per-sub-consumer routes."""

    def test_plain_consumer_route_is_unchanged(self) -> None:
        route = make_route(EchoConsumer)
        assert expand_multiplexed_route(route) == [route]

    def test_route_without_resolved_consumer_is_unchanged(self) -> None:
        """FastAPI discovery reports None for endpoints it cannot resolve."""
        route = make_route(None)
        assert expand_multiplexed_route(route) == [route]

    def test_demultiplexer_expands_to_one_route_per_sub_consumer(self) -> None:
        route = make_route(PlainDemultiplexer)
        expanded = expand_multiplexed_route(route)

        assert [(r.consumer, r.consumer_key) for r in expanded] == [
            (EchoConsumer, "echo"),
            (HealthConsumer, "health"),
        ]
        assert all(r.demultiplexer is PlainDemultiplexer for r in expanded)
        assert all(r.path == route.path for r in expanded)
        assert all(r.base_url == route.base_url for r in expanded)

    def test_demultiplexer_with_own_handlers_keeps_its_own_route(self) -> None:
        route = make_route(HandlerDemultiplexer)
        expanded = expand_multiplexed_route(route)

        assert len(expanded) == 2
        assert expanded[0].consumer is HandlerDemultiplexer
        assert expanded[0].consumer_key is None
        assert expanded[0].demultiplexer is None
        assert expanded[1].consumer is EchoConsumer
        assert expanded[1].consumer_key == "echo"
        assert expanded[1].demultiplexer is HandlerDemultiplexer

    def test_path_params_are_preserved(self) -> None:
        route = RouteInfo(
            path="ws/mux/(?P<room>[^/]+)/",
            handler=object(),
            base_url="ws://localhost:8000",
            consumer=PlainDemultiplexer,
            path_params={"room": "[^/]+"},
        )
        expanded = expand_multiplexed_route(route)

        assert all(r.path_params == {"room": "[^/]+"} for r in expanded)
        assert all(r.channel_path == "ws/mux/{room}/" for r in expanded)
