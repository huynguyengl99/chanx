from concurrent.futures import ThreadPoolExecutor

from django.urls import reverse
from rest_framework.test import APIClient

from asgiref.sync import sync_to_async
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import (
    PongMessage,
)
from test_utils.testing import WebsocketTestCase

from discussion.messages.discussion import (
    DiscussionMemberMessage,
    DiscussionMessagePayload,
    NewDiscussionMessage,
)


class TestDiscussionConsumer(WebsocketTestCase):
    ws_path = "/ws/discussion/"

    async def test_connect_successfully_and_send_and_receive_discussion_messages(
        self,
    ) -> None:
        await self.auth_communicator.connect()

        await self.auth_communicator.assert_authenticated_status_ok()

        # Test ping/pong
        await self.auth_communicator.send_message(PingMessage())
        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [PongMessage().model_dump()]

        # Second connection
        _second_user, second_ws_headers = await self.acreate_user_and_ws_headers()

        second_communicator = self.create_communicator(headers=second_ws_headers)
        await second_communicator.connect()
        await second_communicator.assert_authenticated_status_ok()

        # Test discussion message send and receive from auth user
        await self.auth_communicator.send_message(
            NewDiscussionMessage(payload=DiscussionMessagePayload(content="Hello"))
        )
        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == []  # no echo back

        all_second_user_messages = await second_communicator.receive_all_json(
            wait_group=True
        )
        assert all_second_user_messages == [
            DiscussionMemberMessage(
                payload=DiscussionMessagePayload(content="Hello"),
                is_current=False,
                is_mine=False,
            ).model_dump()
        ]

        # Test discussion message send and receive from another user
        await second_communicator.send_message(
            NewDiscussionMessage(payload=DiscussionMessagePayload(content="Hi"))
        )
        all_second_user_messages = await second_communicator.receive_all_json()
        assert all_second_user_messages == []  # no echo back

        all_messages = await self.auth_communicator.receive_all_json(wait_group=True)
        assert all_messages == [
            DiscussionMemberMessage(
                payload=DiscussionMessagePayload(content="Hi"),
                is_current=False,
                is_mine=False,
            ).model_dump()
        ]

        # Test discussion message send and receive via dict instead message
        await second_communicator.send_message(
            NewDiscussionMessage(
                payload=DiscussionMessagePayload(content="Raw message", raw=True)
            )
        )
        all_second_user_messages = await second_communicator.receive_all_json()
        assert all_second_user_messages == []  # no echo back

        all_messages = await self.auth_communicator.receive_all_json(wait_group=True)
        assert all_messages == [
            {"is_current": False, "is_mine": False, "message": "Raw message"},
        ]

        # Test notification

        notification_message = "Notification message"
        api_client = APIClient()

        with ThreadPoolExecutor(max_workers=1) as executor:
            await sync_to_async(
                api_client.post, thread_sensitive=False, executor=executor
            )(reverse("notify_people"), {"message": notification_message})

        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [
            DiscussionMemberMessage(
                payload=DiscussionMessagePayload(
                    content=f"ATTENTION: {notification_message}"
                ),
                is_current=False,
                is_mine=False,
            ).model_dump()
        ]
