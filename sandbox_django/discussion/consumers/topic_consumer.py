from rest_framework.permissions import IsAuthenticated

from chanx.channels.authenticator import DjangoAuthenticator
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.decorators import event_handler, ws_handler
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
    NewReplyEvent,
    ReplyCreatedMessage,
    TopicDetailEvent,
)
from discussion.models import DiscussionTopic


class DiscussionTopicAuthenticator(DjangoAuthenticator):
    permission_classes = [IsAuthenticated]
    queryset = DiscussionTopic.objects.all()
    obj: DiscussionTopic


class DiscussionTopicConsumer(AsyncJsonWebsocketConsumer[TopicDetailEvent]):
    """
    WebSocket consumer for discussion topic detail view.

    Handles topic-specific operations like replying, voting, and accepting/unaccepting answers.
    """

    authenticator_class = DiscussionTopicAuthenticator
    authenticator: DiscussionTopicAuthenticator

    async def post_authentication(self) -> None:
        assert self.channel_layer

        group_name = f"discussion_topic_{self.authenticator.obj.pk}"

        await self.channel_layer.group_add(group_name, self.channel_name)
        self.groups.append(group_name)

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @event_handler
    async def handle_new_reply(self, event: NewReplyEvent) -> ReplyCreatedMessage:
        return ReplyCreatedMessage(payload=event.payload)

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
