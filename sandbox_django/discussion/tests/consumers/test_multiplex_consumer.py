from rest_framework import status

from chanx.channels.testing import DjangoWebsocketCommunicator
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.testing import WebsocketTestCase

from discussion.consumers.multiplex_consumer import DiscussionMultiplexer
from discussion.messages.topic_list_messages import (
    NewTopicEvent,
    NewTopicEventPayload,
    TopicCreatedMessage,
)


class TestDiscussionMultiplexer(WebsocketTestCase):
    """Tests for serving the discussion consumers over a single route."""

    consumer = DiscussionMultiplexer

    def setUp(self) -> None:
        super().setUp()
        self.ws_path = "/ws/discussion/mux/"

    async def connect_authenticated(self) -> DjangoWebsocketCommunicator:
        """
        Connect and settle the authentication traffic.

        The demultiplexer authenticates the shared connection and reports it
        unwrapped, then every sub-consumer runs its own authenticator and reports
        its own result under its envelope key -- a sub-consumer may well be
        stricter than the demultiplexer.
        """
        communicator = self.auth_communicator
        await communicator.connect()
        await communicator.assert_authenticated_status_ok()

        pending = set(DiscussionMultiplexer.consumers)
        while pending:
            frame = await communicator.receive_json_from()
            key = frame.get("consumer")
            if key in pending and frame["message"]["action"] == "authentication":
                pending.discard(key)

        return communicator

    async def test_connect_and_ping_the_demultiplexer(self) -> None:
        """A frame without an envelope is answered by the demultiplexer itself."""
        await self.connect_authenticated()

        await self.auth_communicator.send_message(PingMessage())

        assert await self.auth_communicator.receive_all_envelopes() == [
            (None, PongMessage())
        ]

    async def test_ping_each_sub_consumer_independently(self) -> None:
        """Each sub-consumer answers under its own envelope key."""
        await self.connect_authenticated()

        await self.auth_communicator.send_message(PingMessage(), consumer="topics")
        assert await self.auth_communicator.receive_all_envelopes(
            stop_consumer="topics"
        ) == [("topics", PongMessage())]

        await self.auth_communicator.send_message(PingMessage(), consumer="group_chat")
        assert await self.auth_communicator.receive_all_envelopes(
            stop_consumer="group_chat"
        ) == [("group_chat", PongMessage())]

    async def test_unknown_consumer_key_is_reported_unwrapped(self) -> None:
        """An unroutable key errors without taking the shared connection down."""
        await self.connect_authenticated()

        await self.auth_communicator.send_json_to(
            {"consumer": "nope", "message": {"action": "ping", "payload": None}}
        )

        response = await self.auth_communicator.receive_json_from()
        assert response["action"] == "error"
        assert response["payload"]["consumer"] == "nope"

        await self.auth_communicator.send_message(PingMessage(), consumer="topics")
        assert await self.auth_communicator.receive_all_envelopes(
            stop_consumer="topics"
        ) == [("topics", PongMessage())]

    async def test_channel_event_reaches_the_owning_sub_consumer(self) -> None:
        """The multiplexed list consumer stays subscribed to its own group."""
        await self.connect_authenticated()

        # Make sure the sub-consumers have joined their groups.
        await self.auth_communicator.send_message(PingMessage(), consumer="topics")
        await self.auth_communicator.receive_all_envelopes(stop_consumer="topics")

        payload = NewTopicEventPayload(
            id=1,
            title="Multiplexed topic",
            author={"id": 1, "username": "someone"},
            vote_count=0,
            reply_count=0,
            has_accepted_answer=False,
            view_count=0,
            created_at="2026-08-04T00:00:00Z",
            formatted_created_at="Aug 4, 2026",
        )
        await DiscussionMultiplexer.consumers["topics"].broadcast_event(
            NewTopicEvent(payload=payload), groups=["discussion_updates"]
        )

        envelopes = await self.auth_communicator.receive_all_envelopes(
            stop_consumer="topics", stop_action="event_complete"
        )
        assert envelopes == [("topics", TopicCreatedMessage(payload=payload))]

    async def test_unauthenticated_user_cannot_connect(self) -> None:
        """The shared connection is authenticated once, by the demultiplexer."""
        unauthenticated = self.create_communicator(
            headers=[(b"origin", b"http://localhost:8000")]
        )

        await unauthenticated.connect()

        auth = await unauthenticated.wait_for_auth(max_auth_time=1000)
        assert auth is not None
        assert auth.payload.status_code == status.HTTP_401_UNAUTHORIZED

        await unauthenticated.assert_closed()
