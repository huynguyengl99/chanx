import asyncio
from typing import Any, Literal
from unittest.mock import patch

from channels.routing import URLRouter
from django.urls import path
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny

import humps
import pytest
from chanx.constants import MISSING_PYHUMPS_ERROR
from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import (
    BaseGroupMessage,
    BaseIncomingMessage,
    BaseMessage,
    BaseOutgoingGroupMessage,
)
from chanx.messages.incoming import IncomingMessage, PingMessage
from chanx.messages.outgoing import PongMessage
from chanx.testing import WebsocketTestCase
from chanx.utils.settings import override_chanx_settings
from pydantic import BaseModel
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


class AnonymousGroupMemberMessage(BaseGroupMessage):
    action: Literal["member_message"] = "member_message"
    payload: Any


class AnonymousGroupMessage(BaseOutgoingGroupMessage):
    group_message: AnonymousGroupMemberMessage


class AnonymousGroupConsumer(AsyncJsonWebsocketConsumer):
    permission_classes = [AllowAny]
    authentication_classes = []
    send_completion = False
    send_message_immediately = True
    silent_actions = {}
    log_received_message = True
    log_sent_message = True
    log_ignored_actions = {}
    send_authentication_message = True
    INCOMING_MESSAGE_SCHEMA = IncomingMessage
    OUTGOING_GROUP_MESSAGE_SCHEMA = AnonymousGroupMessage

    groups = ["anonymous_group"]

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_group_message(
                    AnonymousGroupMemberMessage(payload=PongMessage()),
                    exclude_current=False,
                )


class MyAnonymousGroupTestCase(WebsocketTestCase):
    ws_path = "/anonymous-group/"

    router = URLRouter([path("anonymous-group/", AnonymousGroupConsumer.as_asgi())])

    async def test_send_anonymous_group_message_without_completion(self):
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        await self.auth_communicator.send_message(PingMessage())

        message = await self.auth_communicator.receive_json_from()
        await asyncio.sleep(0.05)  # give some extra time to process any extra thing
        raw_res = AnonymousGroupMemberMessage(payload=PongMessage()).model_dump()
        extended_res = {
            **raw_res,
            "is_current": True,
            "is_mine": False,
        }

        assert message == extended_res


class SnakePayload(BaseModel):
    snake_field: str


class SnakeMessage(BaseMessage):
    action: Literal["snake_message"] = "snake_message"
    payload: SnakePayload


class SnakeIncomingMessage(BaseIncomingMessage):
    message: SnakeMessage


class CamelizeConsumer(AsyncJsonWebsocketConsumer):
    permission_classes = [AllowAny]
    authentication_classes = []
    INCOMING_MESSAGE_SCHEMA = SnakeIncomingMessage

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case SnakeMessage(payload=payload):
                payload: SnakePayload
                await self.send_message(
                    SnakeMessage(
                        payload=SnakePayload(snake_field=f"Reply {payload.snake_field}")
                    )
                )


class CamelizeConsumerTestCase(WebsocketTestCase):
    ws_path = "/camelize-consumer/"

    router = URLRouter([path("camelize-consumer/", CamelizeConsumer.as_asgi())])

    @override_chanx_settings(
        CAMELIZE=True,
    )
    async def test_camelize_case(self):
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth(
            MyConsumer.send_authentication_message
        )
        assert auth.payload.status_code == status.HTTP_200_OK

        message = SnakeMessage(payload=SnakePayload(snake_field="data")).model_dump()
        await self.auth_communicator.send_json_to(humps.camelize(message))
        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [
            {
                "action": "snake_message",
                "payload": {"snakeField": "Reply data"},
            }
        ]

    @override_chanx_settings(
        CAMELIZE=True,
        SEND_AUTHENTICATION_MESSAGE=False,
    )
    @patch("chanx.generic.websocket.humps", None)
    async def test_missing_humps_raises_error(self):
        with pytest.raises(RuntimeError) as excinfo:
            await self.auth_communicator.connect()

        assert MISSING_PYHUMPS_ERROR in str(excinfo.value)
