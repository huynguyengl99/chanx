"""Tests for the close code picked after a failed authentication."""

from collections.abc import MutableMapping
from typing import Any
from unittest.mock import AsyncMock

import pytest
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.authenticator import BaseAuthenticator


class StatusAuthenticator(BaseAuthenticator):
    result_status: int | None = None

    async def authenticate(self, scope: MutableMapping[str, Any]) -> bool:
        self.status_code = self.result_status
        return False


@pytest.mark.parametrize(
    ("status_code", "close_code"),
    [(401, 4401), (403, 4403), (404, 4404), (500, 4500), (None, 4401), (200, 4401)],
)
def test_close_code_follows_status(status_code: int | None, close_code: int) -> None:
    authenticator = StatusAuthenticator(AsyncMock())
    authenticator.status_code = status_code
    assert authenticator.close_code == close_code


@pytest.mark.asyncio
@pytest.mark.parametrize(("status_code", "close_code"), [(403, 4403), (None, 4401)])
async def test_failed_authentication_closes_with_code(
    status_code: int | None, close_code: int
) -> None:
    class Authenticator(StatusAuthenticator):
        result_status = status_code

    class Consumer(AsyncJsonWebsocketConsumer):
        authenticator_class = Authenticator

    consumer = Consumer()
    consumer.scope = {"type": "websocket", "path": "/ws"}
    consumer.authenticator = Authenticator(AsyncMock())
    consumer.accept = AsyncMock()  # type: ignore[method-assign]
    consumer.base_send = AsyncMock()

    await consumer.websocket_connect({"type": "websocket.connect"})

    consumer.base_send.assert_awaited_once_with(
        {"type": "websocket.close", "code": close_code}
    )
