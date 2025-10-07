from typing import cast

from rest_framework import status

from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.testing import WebsocketTestCase

from discussion.consumers.list_consumer import DiscussionListConsumer
from discussion.messages.common_messages import (
    VotePayload,
    VoteUpdatedMessage,
    VoteUpdateEvent,
)
from discussion.messages.topic_detail_messages import (
    AnswerAcceptedEvent,
    AnswerAcceptedEventPayload,
    AnswerAcceptedMessage,
    AnswerUnacceptedEvent,
    AnswerUnacceptedEventPayload,
    AnswerUnacceptedMessage,
)
from discussion.messages.topic_list_messages import (
    NewTopicEvent,
    NewTopicEventPayload,
    TopicCreatedMessage,
)


class TestDiscussionListConsumer(WebsocketTestCase):
    """Unit tests for DiscussionListConsumer - focuses on consumer event handling logic"""

    consumer = DiscussionListConsumer

    def setUp(self) -> None:
        super().setUp()
        self.ws_path = "/ws/discussion/"

    async def test_connect_successfully_and_ping(self) -> None:
        """Test basic connection and ping/pong functionality"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        await self.auth_communicator.send_message(PingMessage())

        all_messages = await self.auth_communicator.receive_all_messages()
        assert all_messages == [PongMessage()]

    async def test_unauthenticated_user_cannot_connect(self) -> None:
        """Test that unauthenticated users cannot connect"""
        # Create communicator without authentication headers
        unauthenticated_communicator = self.create_communicator(
            headers=[
                (b"origin", b"http://localhost:8000"),
            ]
        )

        await unauthenticated_communicator.connect()

        # Check authentication response
        auth = await unauthenticated_communicator.wait_for_auth(max_auth_time=1000)
        assert auth is not None
        assert auth.payload.status_code == status.HTTP_401_UNAUTHORIZED

        # Connection should be closed
        await unauthenticated_communicator.assert_closed()

    async def test_new_topic_event_broadcast(self) -> None:
        """Test consumer handles new topic events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test topic data
        test_topic_payload = NewTopicEventPayload(
            id=123,
            title="New Test Topic",
            author={"id": 1, "email": "author@example.com"},
            vote_count=0,
            reply_count=0,
            has_accepted_answer=False,
            view_count=0,
            created_at="2023-01-01T12:00:00Z",
            formatted_created_at="Jan 01, 2023 at 12:00 PM",
        )

        # Send new topic event to discussion updates group
        await DiscussionListConsumer.broadcast_event(
            NewTopicEvent(payload=test_topic_payload),
            ["discussion_updates"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(TopicCreatedMessage, all_messages[0])
        assert message.action == "topic_created"
        assert message.payload.id == 123
        assert message.payload.title == "New Test Topic"
        assert message.payload.author["email"] == "author@example.com"
        assert message.payload.vote_count == 0
        assert message.payload.reply_count == 0
        assert message.payload.has_accepted_answer is False

    async def test_vote_update_event_broadcast(self) -> None:
        """Test consumer handles vote update events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test vote update payload
        vote_payload = VotePayload(target_type="topic", target_id=456, vote_count=5)

        # Send vote update event
        await DiscussionListConsumer.broadcast_event(
            VoteUpdateEvent(payload=vote_payload),
            ["discussion_updates"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(VoteUpdatedMessage, all_messages[0])
        assert message.action == "vote_updated"
        assert message.payload.target_type == "topic"
        assert message.payload.target_id == 456
        assert message.payload.vote_count == 5

    async def test_answer_accepted_event_broadcast(self) -> None:
        """Test consumer handles answer accepted events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test answer accepted payload
        answer_accepted_payload = AnswerAcceptedEventPayload(
            topic_id=789,
            topic_title="Test Topic with Answer",
            reply_id=101,
            reply_author="replier@example.com",
        )

        # Send answer accepted event
        await DiscussionListConsumer.broadcast_event(
            AnswerAcceptedEvent(payload=answer_accepted_payload),
            ["discussion_updates"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(AnswerAcceptedMessage, all_messages[0])
        assert message.action == "answer_accepted"
        assert message.payload.topic_id == 789
        assert message.payload.topic_title == "Test Topic with Answer"
        assert message.payload.reply_id == 101
        assert message.payload.reply_author == "replier@example.com"

    async def test_answer_unaccepted_event_broadcast(self) -> None:
        """Test consumer handles answer unaccepted events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test answer unaccepted payload
        answer_unaccepted_payload = AnswerUnacceptedEventPayload(
            topic_id=789,
            topic_title="Test Topic Answer Unaccepted",
            reply_id=101,
            reply_author="replier@example.com",
        )

        # Send answer unaccepted event
        await DiscussionListConsumer.broadcast_event(
            AnswerUnacceptedEvent(payload=answer_unaccepted_payload),
            ["discussion_updates"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(AnswerUnacceptedMessage, all_messages[0])
        assert message.action == "answer_unaccepted"
        assert message.payload.topic_id == 789
        assert message.payload.topic_title == "Test Topic Answer Unaccepted"
        assert message.payload.reply_id == 101
        assert message.payload.reply_author == "replier@example.com"

    async def test_events_to_wrong_group_not_received(self) -> None:
        """Test that events sent to other groups are not received"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send event to a different group
        test_topic_payload = NewTopicEventPayload(
            id=999,
            title="Private Topic",
            author={"id": 1, "email": "private@example.com"},
            vote_count=0,
            reply_count=0,
            has_accepted_answer=False,
            view_count=0,
            created_at="2023-01-01T12:00:00Z",
            formatted_created_at="Jan 01, 2023 at 12:00 PM",
        )

        await DiscussionListConsumer.broadcast_event(
            NewTopicEvent(payload=test_topic_payload),
            ["wrong_group_name"],
        )

        # Should not receive any messages
        assert await self.auth_communicator.receive_nothing()
