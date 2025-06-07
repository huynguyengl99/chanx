import asyncio
import sys
from typing import Any, Literal

from channels.routing import URLRouter

from asgiref.timeout import timeout
from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseChannelEvent, BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from chanx.routing import path
from chanx.utils.settings import override_chanx_settings
from pydantic import BaseModel
from structlog.testing import capture_logs
from test_utils.testing import WebsocketTestCase

if sys.version_info < (3, 11):
    from asyncio.exceptions import TimeoutError


class NotifyEvent(BaseChannelEvent):
    class Payload(BaseModel):
        content: str

    handler: Literal["notify"] = "notify"
    payload: Payload


class UnregisteredEvent(BaseChannelEvent):
    handler: Literal["unregistered"] = "unregistered"
    payload: str


class UnhandledEvent(BaseChannelEvent):
    handler: Literal["unhandled"] = "unhandled"
    payload: str


MyEvent = NotifyEvent | UnhandledEvent


class ReplyMessage(BaseMessage):
    action: Literal["reply"] = "reply"
    payload: str


class MyEventsConsumer(AsyncJsonWebsocketConsumer[PingMessage, MyEvent]):
    permission_classes = []
    authentication_classes = []
    groups = ["events"]

    async def receive_message(self, message: PingMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())

    async def receive_event(self, event: MyEvent) -> None:
        match event:
            case NotifyEvent():
                notify_message = f"ATTENTION: {event.payload.content}"

                await self.send_message(ReplyMessage(payload=notify_message))
            case _:
                raise ValueError("Unhandled event")


class MyEventsConsumerTestCase(WebsocketTestCase):
    ws_path = "/events/"

    router = URLRouter([path("events/", MyEventsConsumer.as_asgi())])

    async def test_send_event_complete_successfully(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.assert_authenticated_status_ok()
        await MyEventsConsumer.asend_channel_event(
            "events", NotifyEvent(payload=NotifyEvent.Payload(content="Hello world!"))
        )

        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [
            ReplyMessage(payload="ATTENTION: Hello world!").model_dump(),
        ]

    async def test_sent_unregistered_event(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.assert_authenticated_status_ok()

        with capture_logs() as logs:
            await MyEventsConsumer.asend_channel_event(
                "events",
                UnregisteredEvent(payload="123"),  # type: ignore[arg-type]
            )
            await asyncio.sleep(0.1)  # wait for processing
        err_log = logs[0]
        assert err_log["event"] == "Failed to process channel event"
        assert err_log["log_level"] == "error"
        err_msg = "Input tag 'unregistered' found using 'handler' does not match any of the expected tags: 'notify'"
        assert err_msg in str(err_log["exc_info"])

    async def test_sent_unhandled_event(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.assert_authenticated_status_ok()

        with capture_logs() as logs:
            await MyEventsConsumer.asend_channel_event(
                "events",
                UnhandledEvent(payload="123"),
            )
            await asyncio.sleep(0.1)  # wait for processing
        err_log = logs[0]
        assert err_log["event"] == "Failed to process channel event"
        assert "Unhandled event" in str(err_log["exc_info"])
        assert err_log["log_level"] == "error"

    @override_chanx_settings(
        SEND_COMPLETION=False,
    )
    async def test_send_event_without_completion(self) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.assert_authenticated_status_ok()
        await MyEventsConsumer.asend_channel_event(
            "events", NotifyEvent(payload=NotifyEvent.Payload(content="Hello world!"))
        )
        all_messages: list[dict[str, Any]] = []
        try:
            async with timeout(0.5):
                while True:
                    message: dict[str, Any] = (
                        await self.auth_communicator.receive_json_from()
                    )
                    all_messages.append(message)
        except TimeoutError:
            pass
        assert all_messages == [
            ReplyMessage(payload="ATTENTION: Hello world!").model_dump(),
        ]
