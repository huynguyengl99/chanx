from typing import cast

from rest_framework import status

from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.testing import WebsocketTestCase

from discussion.consumers.topic_consumer import DiscussionTopicConsumer
from discussion.factories import DiscussionTopicFactory
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
    NewReplyEvent,
    NewReplyEventPayload,
    ReplyCreatedMessage,
)


class TestDiscussionTopicConsumer(WebsocketTestCase):
    """Unit tests for DiscussionTopicConsumer - focuses on consumer event handling logic"""

    consumer = DiscussionTopicConsumer

    def setUp(self) -> None:
        super().setUp()
        # Create a discussion topic for testing
        self.topic = DiscussionTopicFactory.create(author=self.user)
        self.ws_path = f"/ws/discussion/{self.topic.pk}/"

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
                (b"x-forwarded-for", b"127.0.0.1"),
            ]
        )

        await unauthenticated_communicator.connect()

        # Check authentication response
        auth = await unauthenticated_communicator.wait_for_auth(max_auth_time=1000)
        assert auth is not None
        assert auth.payload.status_code == status.HTTP_401_UNAUTHORIZED

        # Connection should be closed
        await unauthenticated_communicator.assert_closed()

    async def test_connect_to_nonexistent_topic(self) -> None:
        """Test connecting to a non-existent topic returns 404"""
        # Create communicator for non-existent topic
        nonexistent_communicator = self.create_communicator(
            ws_path="/ws/discussion/99999/", headers=self.ws_headers
        )

        await nonexistent_communicator.connect()

        # Check authentication response - should get 404
        auth = await nonexistent_communicator.wait_for_auth(max_auth_time=1000)
        assert auth is not None
        assert auth.payload.status_code == status.HTTP_404_NOT_FOUND

        # Connection should be closed
        await nonexistent_communicator.assert_closed()

    async def test_new_reply_event_broadcast(self) -> None:
        """Test consumer handles new reply events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test reply data
        test_reply_payload = NewReplyEventPayload(
            id=123,
            content="This is a new reply",
            author={"id": 2, "email": "replier@example.com"},
            vote_count=0,
            is_accepted=False,
            created_at="2023-01-01T12:00:00Z",
            formatted_created_at="Jan 01, 2023 at 12:00 PM",
            topic_id=self.topic.pk,
            topic_title=self.topic.title,
        )

        # Send new reply event to topic-specific group
        await DiscussionTopicConsumer.broadcast_event(
            NewReplyEvent(payload=test_reply_payload),
            [f"discussion_topic_{self.topic.pk}"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(ReplyCreatedMessage, all_messages[0])
        assert message.action == "reply_created"
        assert message.payload.id == 123
        assert message.payload.content == "This is a new reply"
        assert message.payload.author["email"] == "replier@example.com"
        assert message.payload.vote_count == 0
        assert message.payload.is_accepted is False

    async def test_vote_update_event_broadcast(self) -> None:
        """Test consumer handles vote update events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test vote update payload
        vote_payload = VotePayload(target_type="reply", target_id=456, vote_count=3)

        # Send vote update event
        await DiscussionTopicConsumer.broadcast_event(
            VoteUpdateEvent(payload=vote_payload),
            [f"discussion_topic_{self.topic.pk}"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(VoteUpdatedMessage, all_messages[0])
        assert message.action == "vote_updated"
        assert message.payload.target_type == "reply"
        assert message.payload.target_id == 456
        assert message.payload.vote_count == 3

    async def test_answer_accepted_event_broadcast(self) -> None:
        """Test consumer handles answer accepted events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test answer accepted payload
        answer_accepted_payload = AnswerAcceptedEventPayload(
            topic_id=self.topic.pk,
            topic_title=self.topic.title,
            reply_id=789,
            reply_author="answerer@example.com",
        )

        # Send answer accepted event
        await DiscussionTopicConsumer.broadcast_event(
            AnswerAcceptedEvent(payload=answer_accepted_payload),
            [f"discussion_topic_{self.topic.pk}"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(AnswerAcceptedMessage, all_messages[0])
        assert message.action == "answer_accepted"
        assert message.payload.topic_id == self.topic.pk
        assert message.payload.topic_title == self.topic.title
        assert message.payload.reply_id == 789
        assert message.payload.reply_author == "answerer@example.com"

    async def test_answer_unaccepted_event_broadcast(self) -> None:
        """Test consumer handles answer unaccepted events correctly"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create test answer unaccepted payload
        answer_unaccepted_payload = AnswerUnacceptedEventPayload(
            topic_id=self.topic.pk,
            topic_title=self.topic.title,
            reply_id=789,
            reply_author="answerer@example.com",
        )

        # Send answer unaccepted event
        await DiscussionTopicConsumer.broadcast_event(
            AnswerUnacceptedEvent(payload=answer_unaccepted_payload),
            [f"discussion_topic_{self.topic.pk}"],
        )

        # Verify consumer processed and forwarded the event correctly
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = cast(AnswerUnacceptedMessage, all_messages[0])
        assert message.action == "answer_unaccepted"
        assert message.payload.topic_id == self.topic.pk
        assert message.payload.topic_title == self.topic.title
        assert message.payload.reply_id == 789
        assert message.payload.reply_author == "answerer@example.com"

    async def test_events_to_wrong_topic_not_received(self) -> None:
        """Test that events sent to other topics are not received"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send event to a different topic
        test_reply_payload = NewReplyEventPayload(
            id=999,
            content="Private reply",
            author={"id": 1, "email": "private@example.com"},
            vote_count=0,
            is_accepted=False,
            created_at="2023-01-01T12:00:00Z",
            formatted_created_at="Jan 01, 2023 at 12:00 PM",
            topic_id=999,  # Different topic
            topic_title="Different Topic",
        )

        await DiscussionTopicConsumer.broadcast_event(
            NewReplyEvent(payload=test_reply_payload),
            ["discussion_topic_999"],  # Different topic group
        )

        # Should not receive any messages
        assert await self.auth_communicator.receive_nothing()
