from rest_framework.permissions import IsAuthenticated

from chanx.core.decorators import event_handler, ws_handler
from chanx.core.websocket import AsyncJsonWebsocketConsumer
from chanx.ext.channels.authenticator import DjangoAuthenticator
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from discussion.messages.common_messages import (
    VoteUpdatedMessage,
    VoteUpdateEvent,
)
from discussion.messages.topic_detail_messages import (
    AnswerAcceptedEvent,
    AnswerAcceptedMessage,
    AnswerUnacceptedEvent,
    AnswerUnacceptedMessage,
)
from discussion.messages.topic_list_messages import (
    NewTopicEvent,
    TopicCreatedMessage,
    TopicListEvent,
)


class DiscussionListAuthenticator(DjangoAuthenticator):
    permission_classes = [IsAuthenticated]


class DiscussionListConsumer(AsyncJsonWebsocketConsumer[TopicListEvent]):
    """
    WebSocket consumer for discussion topic list view.

    Handles global discussion updates like new topics, votes, and answer acceptance/unacceptance.
    """

    authenticator_class = DiscussionListAuthenticator
    authenticator: DiscussionListAuthenticator
    groups = ["discussion_updates"]

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @event_handler
    async def handle_new_topic(self, event: NewTopicEvent) -> TopicCreatedMessage:
        return TopicCreatedMessage(payload=event.payload)

    @event_handler
    async def handle_vote_update(self, event: VoteUpdateEvent) -> VoteUpdatedMessage:
        return VoteUpdatedMessage(payload=event.payload)

    @event_handler
    async def handle_accept_answer(
        self, event: AnswerAcceptedEvent
    ) -> AnswerAcceptedMessage:
        return AnswerAcceptedMessage(payload=event.payload)

    @event_handler
    async def handle_unaccept_answer(
        self, event: AnswerUnacceptedEvent
    ) -> AnswerUnacceptedMessage:
        return AnswerUnacceptedMessage(payload=event.payload)
