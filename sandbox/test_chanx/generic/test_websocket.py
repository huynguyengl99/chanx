import asyncio
from typing import Any, Literal
from unittest.mock import patch

from channels.routing import URLRouter
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny

import humps
import pytest
from chanx.constants import MISSING_PYHUMPS_ERROR
from chanx.generic.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import (
    BaseGroupMessage,
    BaseMessage,
)
from chanx.messages.incoming import IncomingMessage, PingMessage
from chanx.messages.outgoing import PongMessage
from chanx.routing import path
from chanx.testing import WebsocketTestCase
from chanx.utils.settings import override_chanx_settings
from pydantic import BaseModel
from structlog.testing import capture_logs


class MyConsumer(AsyncJsonWebsocketConsumer[IncomingMessage]):
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication]
    send_completion = True
    send_message_immediately = True
    log_received_message = True
    log_sent_message = True
    log_ignored_actions = set()
    send_authentication_message = True

    async def receive_message(self, message: IncomingMessage, **kwargs: Any) -> None:
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
    async def test_prepopulated_attributes_consumer(self) -> None:
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth(
            MyConsumer.send_authentication_message
        )
        assert auth
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

    async def test_override_wait_for_auth(self) -> None:
        await self.auth_communicator.connect()

        res = await self.auth_communicator.wait_for_auth(False, 0.2)
        assert not res


class InvalidConsumer(AsyncJsonWebsocketConsumer[IncomingMessage]):
    async def receive_message(self, message: IncomingMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_message(PongMessage())


class InvalidConsumerTestCase(WebsocketTestCase):
    ws_path = "/invalid/"

    router = URLRouter([path("invalid/", InvalidConsumer.as_asgi())])

    async def test_connect_invalid_consumer(self) -> None:
        try:
            await self.auth_communicator.connect(0.1)
        except ValueError as e:
            assert str(e) == "INCOMING_MESSAGE_SCHEMA attribute is required."


class NotImplementedConsumer(AsyncJsonWebsocketConsumer[IncomingMessage]):
    pass


class NotImplementedConsumerTestCase(WebsocketTestCase):
    ws_path = "/not-implemented/"

    router = URLRouter([path("not-implemented/", NotImplementedConsumer.as_asgi())])

    async def test_consumer_not_implemented_error(self) -> None:
        with pytest.raises(
            TypeError, match=r"Can't instantiate abstract class NotImplementedConsumer"
        ):
            await self.auth_communicator.connect(0.1)


class AnonymousGroupMemberMessage(BaseGroupMessage):
    action: Literal["member_message"] = "member_message"
    payload: Any


AnonymousGroupMessage = AnonymousGroupMemberMessage


class AnonymousGroupConsumer(
    AsyncJsonWebsocketConsumer[IncomingMessage, None, AnonymousGroupMessage]
):
    permission_classes = [AllowAny]
    authentication_classes = []
    send_completion = False
    send_message_immediately = True
    log_received_message = True
    log_sent_message = True
    log_ignored_actions = set()
    send_authentication_message = True

    groups = ["anonymous_group"]

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case PingMessage():
                await self.send_group_message(
                    AnonymousGroupMemberMessage(payload=PongMessage()),
                    exclude_current=False,
                )
            case _:
                pass


class MyAnonymousGroupTestCase(WebsocketTestCase):
    ws_path = "/anonymous-group/"

    router = URLRouter([path("anonymous-group/", AnonymousGroupConsumer.as_asgi())])

    async def test_send_anonymous_group_message_without_completion(self) -> None:
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


SnakeIncomingMessage = SnakeMessage


class CamelizeConsumer(AsyncJsonWebsocketConsumer[SnakeIncomingMessage]):
    permission_classes = [AllowAny]
    authentication_classes = []

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        match message:
            case SnakeMessage(payload=snake_payload):
                await self.send_message(
                    SnakeMessage(
                        payload=SnakePayload(
                            snake_field=f"Reply {snake_payload.snake_field}"
                        )
                    )
                )
            case _:
                pass


class CamelizeConsumerTestCase(WebsocketTestCase):
    ws_path = "/camelize-consumer/"

    router = URLRouter([path("camelize-consumer/", CamelizeConsumer.as_asgi())])

    @override_chanx_settings(
        CAMELIZE=True,
    )
    async def test_camelize_case(self) -> None:
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth(
            MyConsumer.send_authentication_message
        )
        assert auth
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
    async def test_missing_humps_raises_error(self) -> None:
        with pytest.raises(RuntimeError) as excinfo:
            await self.auth_communicator.connect()

        assert MISSING_PYHUMPS_ERROR in str(excinfo.value)


class TestInitSubclassValidation:
    """Test cases for __init_subclass__ validation."""

    def test_missing_generic_parameter_raises_error(self) -> None:
        """Test that defining a consumer without generic parameters raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            # This should trigger the ValueError in __init_subclass__
            class InvalidConsumerNoGenerics(AsyncJsonWebsocketConsumer):  # type: ignore[type-arg]
                permission_classes = [AllowAny]

                async def receive_message(self, message: Any, **kwargs: Any) -> None:
                    pass

        # Verify the error message contains the expected content
        error_message = str(excinfo.value)
        assert "InvalidConsumerNoGenerics" in error_message
        assert (
            "must specify at least the incoming message type as a generic parameter"
            in error_message
        )
        assert (
            "Hint: class InvalidConsumerNoGenerics(AsyncJsonWebsocketConsumer[YourMessageType])"
            in error_message
        )

    def test_consumer_with_no_matching_base_class(self) -> None:
        """Test that a consumer with no matching AsyncJsonWebsocketConsumer base doesn't set schemas."""

        # Create a consumer that inherits from a different base but still has orig_bases
        class SomeOtherBase:
            pass

        class ConsumerWithDifferentBase(
            AsyncJsonWebsocketConsumer[IncomingMessage], SomeOtherBase
        ):
            permission_classes = [AllowAny]

            async def receive_message(
                self, message: IncomingMessage, **kwargs: Any
            ) -> None:
                pass

        # This should work fine and set the schemas from the AsyncJsonWebsocketConsumer[IncomingMessage] base
        assert (
            getattr(ConsumerWithDifferentBase, "_INCOMING_MESSAGE_SCHEMA")
            == IncomingMessage
        )  # noqa

    def test_consumer_inheriting_from_another_consumer(self) -> None:
        """Test that a consumer inheriting from another consumer doesn't trigger validation again."""

        # First create a valid consumer
        class BaseConsumer(AsyncJsonWebsocketConsumer[IncomingMessage]):
            permission_classes = [AllowAny]

            async def receive_message(
                self, message: IncomingMessage, **kwargs: Any
            ) -> None:
                pass

        # Then inherit from it - this should not trigger the ValueError
        # because it doesn't have AsyncJsonWebsocketConsumer as a direct base
        class DerivedConsumer(BaseConsumer):
            authentication_classes = [SessionAuthentication]

        # Verify it inherits the schemas
        assert getattr(DerivedConsumer, "_INCOMING_MESSAGE_SCHEMA") == IncomingMessage

    def test_valid_generic_parameter_works(self) -> None:
        """Test that defining a consumer with proper generic parameters works."""

        # This should NOT raise an error
        class ValidConsumerWithGenerics(AsyncJsonWebsocketConsumer[IncomingMessage]):
            permission_classes = [AllowAny]

            async def receive_message(
                self, message: IncomingMessage, **kwargs: Any
            ) -> None:
                pass

        # Verify the schemas were set correctly
        assert (
            getattr(ValidConsumerWithGenerics, "_INCOMING_MESSAGE_SCHEMA")
            == IncomingMessage
        )
        assert (
            getattr(ValidConsumerWithGenerics, "_OUTGOING_GROUP_MESSAGE_SCHEMA") is None
        )

    def test_multiple_generic_parameters_works(self) -> None:
        """Test that defining a consumer with multiple generic parameters works."""

        class MultiGenericConsumer(
            AsyncJsonWebsocketConsumer[IncomingMessage, None, AnonymousGroupMessage]
        ):
            permission_classes = [AllowAny]

            async def receive_message(
                self, message: IncomingMessage, **kwargs: Any
            ) -> None:
                pass

        # Verify both schemas were set correctly
        assert (
            getattr(MultiGenericConsumer, "_INCOMING_MESSAGE_SCHEMA") == IncomingMessage
        )
        assert (
            getattr(MultiGenericConsumer, "_OUTGOING_GROUP_MESSAGE_SCHEMA")
            == AnonymousGroupMessage
        )
