from typing import cast

import pytest
from chanx.constants import GROUP_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from chanx.testing import WebsocketCommunicator

from sandbox_fastapi.apps.room_chat.consumer import RoomChatConsumer
from sandbox_fastapi.apps.room_chat.messages import (
    RoomChatMessage,
    RoomMessagePayload,
    RoomNotificationMessage,
)
from sandbox_fastapi.main import app


@pytest.mark.asyncio
async def test_room_chat_ping() -> None:
    room_name = "my-room"
    async with WebsocketCommunicator(
        app, f"/ws/room/{room_name}", consumer=RoomChatConsumer
    ) as comm:
        await comm.send_message(PingMessage())

        replies = await comm.receive_all_messages()
        assert replies == [PongMessage()]


@pytest.mark.asyncio
async def test_room_chat_broadcast_messaging() -> None:
    room_name = "my-room"
    first_comm = WebsocketCommunicator(
        app, f"/ws/room/{room_name}", consumer=RoomChatConsumer
    )
    second_comm = WebsocketCommunicator(
        app, f"/ws/room/{room_name}", consumer=RoomChatConsumer
    )

    await first_comm.connect()
    assert await first_comm.receive_nothing()

    await second_comm.connect()

    notified_messages = await first_comm.receive_all_messages(
        stop_action=GROUP_ACTION_COMPLETE
    )
    assert len(notified_messages) == 1
    notified_message = cast(RoomNotificationMessage, notified_messages[0])
    assert notified_message.payload.message == f"🚪 Someone joined room '{room_name}'"

    assert await second_comm.receive_nothing()

    room_message = "This is a test message"
    expected_message = RoomNotificationMessage(
        payload=RoomMessagePayload(message=f"💬 {room_message}", room_name=room_name)
    )

    await first_comm.send_message(
        RoomChatMessage(payload=RoomMessagePayload(message=room_message))
    )

    first_comm_replies = await first_comm.receive_all_messages(
        stop_action=GROUP_ACTION_COMPLETE
    )
    assert len(first_comm_replies) == 1
    assert first_comm_replies == [expected_message]

    second_comm_replies = await second_comm.receive_all_messages(
        stop_action=GROUP_ACTION_COMPLETE
    )
    assert len(second_comm_replies) == 1
    assert second_comm_replies == [expected_message]

    await first_comm.disconnect()
    await second_comm.disconnect()
