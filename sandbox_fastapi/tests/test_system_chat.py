from typing import cast

import pytest
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from chanx.testing import WebsocketCommunicator

from sandbox_fastapi.apps.system_chat.consumer import SystemMessageConsumer
from sandbox_fastapi.apps.system_chat.messages import (
    MessagePayload,
    SystemEchoMessage,
    UserMessage,
)
from sandbox_fastapi.main import app


@pytest.mark.asyncio
async def test_system_socket() -> None:
    async with WebsocketCommunicator(
        app, "/ws/system", consumer=SystemMessageConsumer
    ) as comm:
        init_messages = await comm.receive_all_messages(stop_action="system_echo")
        assert len(init_messages) == 1

        init_message = cast(SystemEchoMessage, init_messages[0])
        assert init_message.payload.message == "🔧 System: Connection established!"

        await comm.send_message(PingMessage())

        replies = await comm.receive_all_messages()
        assert len(replies) == 1
        assert replies == [PongMessage()]

        test_message = "This is a test message"
        await comm.send_message(
            UserMessage(payload=MessagePayload(message=test_message))
        )
        replies = await comm.receive_all_messages()
        assert len(replies) == 1
        assert replies == [
            SystemEchoMessage(
                payload=MessagePayload(message=f"🔧 System Echo: {test_message}")
            )
        ]
