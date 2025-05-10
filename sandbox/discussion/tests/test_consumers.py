from django.conf import settings

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

        # Test anonymous connection
        anonymous_communicator = self.create_communicator(
            headers=[
                (b"origin", settings.SERVER_URL.encode()),
            ]
        )
        await anonymous_communicator.connect()
        await anonymous_communicator.assert_authenticated_status_ok()

        # Test discussion message send and receive from auth user
        await self.auth_communicator.send_message(
            NewDiscussionMessage(payload=DiscussionMessagePayload(content="Hello"))
        )
        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == []  # no echo back

        all_anonymous_messages = await anonymous_communicator.receive_all_json(
            wait_group=True
        )
        assert all_anonymous_messages == [
            DiscussionMemberMessage(
                payload=DiscussionMessagePayload(content="Hello"),
                is_current=False,
                is_mine=False,
            ).model_dump()
        ]

        # Test discussion message send and receive from anonymous user
        await anonymous_communicator.send_message(
            NewDiscussionMessage(payload=DiscussionMessagePayload(content="Hi"))
        )
        all_anonymous_messages = await anonymous_communicator.receive_all_json()
        assert all_anonymous_messages == []  # no echo back

        all_messages = await self.auth_communicator.receive_all_json(wait_group=True)
        assert all_messages == [
            DiscussionMemberMessage(
                payload=DiscussionMessagePayload(content="Hi"),
                is_current=False,
                is_mine=False,
            ).model_dump()
        ]

        # Test discussion message send and receive via dict instead message
        await anonymous_communicator.send_message(
            NewDiscussionMessage(
                payload=DiscussionMessagePayload(content="Raw message", raw=True)
            )
        )
        all_anonymous_messages = await anonymous_communicator.receive_all_json()
        assert all_anonymous_messages == []  # no echo back

        all_messages = await self.auth_communicator.receive_all_json(wait_group=True)
        assert all_messages == [
            {"is_current": False, "is_mine": False, "message": "Raw message"},
        ]
