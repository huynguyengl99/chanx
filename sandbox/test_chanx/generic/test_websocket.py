from typing import Any

from channels.routing import URLRouter
from django.urls import path
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny

import pytest
from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.messages.incoming import IncomingMessage, PingMessage
from chanx.messages.outgoing import PongMessage
from chanx.testing import WebsocketTestCase
from chanx.utils.settings import override_chanx_settings
from structlog.testing import capture_logs


class MyConsumer(AsyncJsonWebsocketConsumer):
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication]
    send_completion = True
    send_message_immediately = True
    silent_actions = {}
    log_received_message = True
    log_sent_message = True
    log_ignored_actions = {}
    send_authentication_message = True
    INCOMING_MESSAGE_SCHEMA = IncomingMessage

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())


class MyConsumerTestCase(WebsocketTestCase):
    ws_path = "/my-consumer/"

    router = URLRouter([path("my-consumer/", MyConsumer.as_asgi())])

    @override_chanx_settings(
        SEND_COMPLETION=False,
        SEND_MESSAGE_IMMEDIATELY=False,
        SEND_AUTHENTICATION_MESSAGE=False,
        LOG_RECEIVED_MESSAGE=False,
        LOG_SENT_MESSAGE=False,
        LOG_IGNORED_ACTIONS=[],
    )
    async def test_prepopulated_attributes_consumer(self):
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth(
            MyConsumer.send_authentication_message
        )
        assert auth.payload.status_code == status.HTTP_200_OK

        with capture_logs() as cap_logs:
            await self.auth_communicator.send_message(PingMessage())
            all_messages = await self.auth_communicator.receive_all_json()
            assert all_messages == [PongMessage().model_dump()]

        assert cap_logs == [
            {"event": "Received websocket json", "log_level": "info"},
            {
                "sent_action": "pong",
                "event": "Sent websocket json",
                "log_level": "info",
            },
        ]

    async def test_override_wait_for_auth(self):
        await self.auth_communicator.connect()

        res = await self.auth_communicator.wait_for_auth(False, 0.2)
        assert not res


class InvalidConsumer(AsyncJsonWebsocketConsumer):
    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())


class InvalidConsumerTestCase(WebsocketTestCase):
    ws_path = "/invalid/"

    router = URLRouter([path("invalid/", InvalidConsumer.as_asgi())])

    async def test_connect_invalid_consumer(self):
        try:
            await self.auth_communicator.connect(0.1)
        except ValueError as e:
            assert str(e) == "INCOMING_MESSAGE_SCHEMA attribute is required."


class NotImplementedConsumer(AsyncJsonWebsocketConsumer):
    INCOMING_MESSAGE_SCHEMA = IncomingMessage


class NotImplementedConsumerTestCase(WebsocketTestCase):
    ws_path = "/not-implemented/"

    router = URLRouter([path("not-implemented/", NotImplementedConsumer.as_asgi())])

    async def test_consumer_not_implemented_error(self):
        with pytest.raises(
            TypeError, match=r"Can't instantiate abstract class NotImplementedConsumer"
        ):
            await self.auth_communicator.connect(0.1)
