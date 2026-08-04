"""
End-to-end tests for WebSocket multiplexing over Django Channels.

Exercises the demultiplexer through a real ASGI connection: envelope routing in
both directions, fall-through to the demultiplexer's own handlers, isolation of a
sub-consumer that closes, group broadcasting and channel events reaching the
right sub-consumer, and sub-consumer shutdown on disconnect.
"""

from collections.abc import MutableMapping
from typing import Any, ClassVar, Literal

from channels.routing import URLRouter

from chanx.channels.multiplex import AsyncJsonWebsocketDemultiplexer
from chanx.channels.routing import path
from chanx.channels.testing import WebsocketTestCase
from chanx.channels.utils.settings import override_chanx_settings
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.constants import GROUP_ACTION_COMPLETE
from chanx.core.authenticator import BaseAuthenticator
from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #


class EchoMessage(BaseMessage):
    action: Literal["echo"] = "echo"
    payload: str


class EchoReply(BaseMessage):
    action: Literal["echo_reply"] = "echo_reply"
    payload: str


class NestedPayload(BaseModel):
    first_field: str
    other_field: int


class NestedMessage(BaseMessage):
    action: Literal["nested"] = "nested"
    payload: NestedPayload


class NestedReply(BaseMessage):
    action: Literal["nested_reply"] = "nested_reply"
    payload: NestedPayload


class ChatMessage(BaseMessage):
    action: Literal["chat"] = "chat"
    payload: str


class ChatBroadcast(BaseMessage):
    action: Literal["chat_broadcast"] = "chat_broadcast"
    payload: str


class NotifyEvent(BaseMessage):
    action: Literal["notify"] = "notify"
    payload: str


class NotifyOut(BaseMessage):
    action: Literal["notify_out"] = "notify_out"
    payload: str


class SecretMessage(BaseMessage):
    action: Literal["secret"] = "secret"
    payload: None = None


# --------------------------------------------------------------------------- #
# Sub-consumers
# --------------------------------------------------------------------------- #


class EchoConsumer(AsyncJsonWebsocketConsumer):
    """Sub-consumer echoing messages back."""

    @ws_handler
    async def handle_echo(self, message: EchoMessage) -> EchoReply:
        return EchoReply(payload=f"echo: {message.payload}")

    @ws_handler
    async def handle_nested(self, message: NestedMessage) -> NestedReply:
        payload = message.payload
        payload.first_field = f"echo: {payload.first_field}"
        return NestedReply(payload=payload)

    @ws_handler
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        """Shares the `ping` action with the demultiplexer on purpose."""
        return PongMessage()


class ChatConsumer(AsyncJsonWebsocketConsumer[NotifyEvent]):
    """Sub-consumer using groups, broadcasting and channel events."""

    groups = ["mux_chat"]
    disconnected: ClassVar[list[str]] = []

    @ws_handler(output_type=ChatBroadcast)
    async def handle_chat(self, message: ChatMessage) -> None:
        await self.broadcast_message(ChatBroadcast(payload=f"chat: {message.payload}"))

    @ws_handler
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @event_handler
    async def handle_notify(self, event: NotifyEvent) -> NotifyOut:
        return NotifyOut(payload=f"notified: {event.payload}")

    async def websocket_disconnect(self, message: Any) -> None:
        """Record the shutdown so tests can assert sub-consumers are torn down."""
        ChatConsumer.disconnected.append(self.channel_name)
        await super().websocket_disconnect(message)


class DenyingAuthenticator(BaseAuthenticator):
    """Authenticator that always rejects the connection."""

    async def authenticate(self, scope: MutableMapping[str, Any]) -> bool:
        return False


class DeniedConsumer(AsyncJsonWebsocketConsumer):
    """Sub-consumer whose authenticator always denies the connection."""

    authenticator_class = DenyingAuthenticator

    @ws_handler
    async def handle_secret(self, _message: SecretMessage) -> EchoReply:
        return EchoReply(payload="should never be reachable")


# --------------------------------------------------------------------------- #
# Demultiplexers
# --------------------------------------------------------------------------- #


class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    """Demultiplexer with its own top-level ping handler."""

    consumers = {"echo": EchoConsumer, "chat": ChatConsumer}

    @ws_handler
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()


class StreamDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    """Demultiplexer using custom envelope field names."""

    consumers = {"echo": EchoConsumer}
    envelope_consumer_field = "stream"
    envelope_message_field = "data"


class DenyingDemultiplexer(AsyncJsonWebsocketDemultiplexer):
    """Demultiplexer where one sub-consumer denies the connection."""

    consumers = {"echo": EchoConsumer, "denied": DeniedConsumer}


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


class TestMultiplexRouting(WebsocketTestCase):
    """Test envelope routing in both directions."""

    ws_path = "/mux/"
    router = URLRouter([path("mux/", MainDemultiplexer.as_asgi())])
    consumer = MainDemultiplexer

    async def test_message_is_routed_to_named_consumer(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(
            EchoMessage(payload="hello"), consumer="echo"
        )

        response = await self.auth_communicator.receive_json_from()
        assert response == {
            "consumer": "echo",
            "message": EchoReply(payload="echo: hello").model_dump(),
        }

    async def test_messages_are_routed_to_independent_consumers(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(
            EchoMessage(payload="one"), consumer="echo"
        )
        await self.auth_communicator.send_message(
            ChatMessage(payload="two"), consumer="chat"
        )

        envelopes = await self.auth_communicator.receive_all_envelopes(
            stop_action=GROUP_ACTION_COMPLETE
        )

        assert sorted(envelopes, key=lambda pair: str(pair[0])) == [
            ("chat", ChatBroadcast(payload="chat: two")),
            ("echo", EchoReply(payload="echo: one")),
        ]

    @override_chanx_settings(SEND_COMPLETION=False)
    async def test_shared_action_is_disambiguated_by_consumer(self) -> None:
        """Both the demultiplexer and a sub-consumer handle `ping`."""
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(PingMessage(), consumer="echo")
        await self.auth_communicator.send_message(PingMessage())

        envelopes = await self.auth_communicator.receive_all_envelopes()

        assert envelopes == [("echo", PongMessage()), (None, PongMessage())]

    async def test_unenveloped_message_falls_through_to_demultiplexer(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(PingMessage())

        response = await self.auth_communicator.receive_json_from()
        assert response == PongMessage().model_dump()

    async def test_unknown_consumer_key_errors_without_closing(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_json_to(
            {"consumer": "nope", "message": {"action": "echo", "payload": "hi"}}
        )

        response = await self.auth_communicator.receive_json_from()
        assert response["action"] == "error"
        assert response["payload"]["consumer"] == "nope"

        # The shared socket is still usable.
        await self.auth_communicator.send_message(
            EchoMessage(payload="still here"), consumer="echo"
        )
        follow_up = await self.auth_communicator.receive_json_from()
        assert follow_up["consumer"] == "echo"

    async def test_malformed_envelope_reports_validation_error(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_json_to({"consumer": "echo"})

        response = await self.auth_communicator.receive_json_from()
        assert response["action"] == "error"
        assert any(
            error.get("loc") == ["message"] for error in response["payload"]
        ), response["payload"]

    async def test_unknown_action_inside_envelope_errors_from_sub_consumer(
        self,
    ) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_json_to(
            {"consumer": "echo", "message": {"action": "nonexistent", "payload": 1}}
        )

        response = await self.auth_communicator.receive_json_from()
        assert response["consumer"] == "echo"
        assert response["message"]["action"] == "error"

    @override_chanx_settings(CAMELIZE=True)
    async def test_inner_message_is_camelized(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(
            NestedMessage(payload=NestedPayload(first_field="a", other_field=2)),
            consumer="echo",
        )

        response = await self.auth_communicator.receive_json_from()
        assert response["consumer"] == "echo"
        assert "firstField" in response["message"]["payload"]
        assert "first_field" not in response["message"]["payload"]

    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_completion_is_enveloped_per_consumer(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(
            EchoMessage(payload="hello"), consumer="echo"
        )

        messages = await self.auth_communicator.receive_all_json()
        assert messages[-1] == {
            "consumer": "echo",
            "message": {"action": "complete", "payload": None},
        }


class TestMultiplexCustomEnvelopeFields(WebsocketTestCase):
    """Test a demultiplexer with custom envelope field names."""

    ws_path = "/stream-mux/"
    router = URLRouter([path("stream-mux/", StreamDemultiplexer.as_asgi())])
    consumer = StreamDemultiplexer

    async def test_custom_field_names_are_used_on_the_wire(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(
            EchoMessage(payload="hello"), consumer="echo"
        )

        response = await self.auth_communicator.receive_json_from()
        assert response == {
            "stream": "echo",
            "data": EchoReply(payload="echo: hello").model_dump(),
        }

    async def test_communicator_unwraps_custom_field_names(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.send_message(
            EchoMessage(payload="hello"), consumer="echo"
        )

        envelopes = await self.auth_communicator.receive_all_envelopes()
        assert envelopes == [("echo", EchoReply(payload="echo: hello"))]


class TestMultiplexChildIsolation(WebsocketTestCase):
    """Test that a sub-consumer closing does not take the shared socket down."""

    ws_path = "/denying-mux/"
    router = URLRouter([path("denying-mux/", DenyingDemultiplexer.as_asgi())])
    consumer = DenyingDemultiplexer

    async def test_denied_consumer_is_isolated(self) -> None:
        await self.auth_communicator.connect()

        # Connecting reports the denied sub-consumer, unwrapped.
        notice = await self.auth_communicator.receive_json_from()
        assert notice["action"] == "error"
        assert notice["payload"]["consumer"] == "denied"

        # The denied key is no longer routable.
        await self.auth_communicator.send_message(SecretMessage(), consumer="denied")
        response = await self.auth_communicator.receive_json_from()
        assert response["action"] == "error"
        assert response["payload"]["consumer"] == "denied"

        # The healthy sub-consumer still works.
        await self.auth_communicator.send_message(
            EchoMessage(payload="alive"), consumer="echo"
        )
        follow_up = await self.auth_communicator.receive_json_from()
        assert follow_up == {
            "consumer": "echo",
            "message": EchoReply(payload="echo: alive").model_dump(),
        }


class TestMultiplexGroupsAndEvents(WebsocketTestCase):
    """Test that sub-consumers keep their own channel layer subscriptions."""

    ws_path = "/mux/"
    router = URLRouter([path("mux/", MainDemultiplexer.as_asgi())])
    consumer = MainDemultiplexer

    def setUp(self) -> None:
        super().setUp()
        ChatConsumer.disconnected = []

    @staticmethod
    async def drain(communicator: Any) -> None:
        """
        Round-trip a message through the chat sub-consumer.

        Chanx accepts a connection before joining groups, so a test that wants to
        observe group traffic has to wait until the sub-consumer is subscribed.
        """
        await communicator.send_message(PingMessage(), consumer="chat")
        await communicator.receive_all_envelopes(stop_consumer="chat")

    async def test_broadcast_reaches_every_connection_enveloped(self) -> None:
        first = self.auth_communicator
        second = self.create_communicator()
        await first.connect()
        await second.connect()
        await self.drain(first)
        await self.drain(second)

        await first.send_message(ChatMessage(payload="hi all"), consumer="chat")

        expected = [("chat", ChatBroadcast(payload="chat: hi all"))]
        assert (
            await first.receive_all_envelopes(stop_action=GROUP_ACTION_COMPLETE)
            == expected
        )
        assert (
            await second.receive_all_envelopes(stop_action=GROUP_ACTION_COMPLETE)
            == expected
        )

    async def test_channel_event_reaches_the_owning_sub_consumer(self) -> None:
        await self.auth_communicator.connect()
        await self.drain(self.auth_communicator)

        await ChatConsumer.broadcast_event(
            NotifyEvent(payload="from outside"), groups=["mux_chat"]
        )

        envelopes = await self.auth_communicator.receive_all_envelopes(
            stop_action="event_complete"
        )
        assert envelopes == [("chat", NotifyOut(payload="notified: from outside"))]

    async def test_sub_consumers_are_shut_down_on_disconnect(self) -> None:
        await self.auth_communicator.connect()
        await self.drain(self.auth_communicator)

        assert ChatConsumer.disconnected == []

        await self.auth_communicator.disconnect()

        assert len(ChatConsumer.disconnected) == 1

    async def test_group_membership_is_released_on_disconnect(self) -> None:
        first = self.auth_communicator
        second = self.create_communicator()
        await first.connect()
        await second.connect()
        await self.drain(first)
        await self.drain(second)

        await second.disconnect()

        await first.send_message(ChatMessage(payload="alone"), consumer="chat")

        # Only this connection is still in the group, so exactly one copy arrives.
        envelopes = await first.receive_all_envelopes(stop_action=GROUP_ACTION_COMPLETE)
        assert envelopes == [("chat", ChatBroadcast(payload="chat: alone"))]
