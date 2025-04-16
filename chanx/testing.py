import asyncio
from typing import Any

from channels.testing import WebsocketCommunicator as BaseWebsocketCommunicator
from django.test import TestCase

from asgiref.timeout import timeout as async_timeout

from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import ACTION_COMPLETE, AuthenticationMessage
from chanx.settings import chanx_settings
from chanx.utils.asgi import get_websocket_application


class WebsocketCommunicator(BaseWebsocketCommunicator):  # type: ignore
    async def receive_all_json(self, timeout: int = 5) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        async with async_timeout(timeout):
            while True:
                message = await self.receive_json_from(timeout)
                message_action = message.get(chanx_settings.MESSAGE_ACTION_KEY)
                if message_action == ACTION_COMPLETE:
                    break
                messages.append(message)
        return messages

    async def send_message(self, message: BaseMessage) -> None:
        await self.send_json_to(message.model_dump())

    async def wait_for_auth(
        self, max_auth_time: int = 1
    ) -> AuthenticationMessage | None:
        if chanx_settings.SEND_AUTHENTICATION_MESSAGE:
            json_message = await self.receive_json_from(max_auth_time)
            return AuthenticationMessage.model_validate(json_message)
        else:
            await asyncio.sleep(max_auth_time)
            return None


class WebsocketTestCase(TestCase):
    ws_path: str | None = None
    router: Any = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not cls.ws_path:
            raise ValueError("ws_path is not set")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._auth_communicator_instance: WebsocketCommunicator | None = None

        if not self.router:
            # First try to get the complete WebSocket application with middleware
            ws_app = get_websocket_application()
            if ws_app:
                self.router = ws_app
            else:
                raise ValueError(
                    "Could not obtain a WebSocket application. Make sure your ASGI application is properly configured"
                    " with a 'websocket' handler in the ProtocolTypeRouter."
                )

    def get_ws_headers(self) -> list[tuple[bytes, bytes]]:
        return []

    def get_subprotocols(self) -> list[str]:
        return []

    def setUp(self) -> None:
        super().setUp()
        self.ws_headers: list[tuple[bytes, bytes]] = self.get_ws_headers()
        self.subprotocols: list[str] = self.get_subprotocols()
        self._auth_communicator_instance = None

    def tearDown(self) -> None:
        self._auth_communicator_instance = None

    @property
    def auth_communicator(self) -> WebsocketCommunicator:
        if not self._auth_communicator_instance:
            self._auth_communicator_instance = WebsocketCommunicator(
                self.router,
                self.ws_path,
                headers=self.ws_headers,
                subprotocols=self.subprotocols,
            )

        return self._auth_communicator_instance
