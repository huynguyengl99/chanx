from chanx.core.decorators import channel, event_handler, ws_handler
from chanx.core.websocket import AsyncJsonWebsocketConsumer
from chanx.ext.channels.authenticator import DjangoAuthenticator
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage

from assistants.messages.assistant import (
    AssistantErrorMessage,
    AssistantEvent,
    CompleteStreamingEvent,
    CompleteStreamingMessage,
    ErrorEvent,
    NewAssistantMessage,
    NewAssistantMessageEvent,
    StreamingEvent,
    StreamingMessage,
)
from assistants.models import AssistantConversation
from assistants.permissions import ConversationOwner


class AssistantAuthenticator(DjangoAuthenticator):
    permission_classes = [ConversationOwner]
    queryset = AssistantConversation.objects.all()
    obj: AssistantConversation


@channel(
    name="assistants", description="AI Assistant WebSocket API", tags=["ai", "chat"]
)
class ConversationAssistantConsumer(AsyncJsonWebsocketConsumer[AssistantEvent]):
    """WebSocket consumer for both authenticated and anonymous users with specific conversations."""

    authenticator_class = AssistantAuthenticator
    authenticator: AssistantAuthenticator

    log_ignored_actions = ["streaming"]

    async def post_authentication(self) -> None:
        assert self.channel_layer
        conversation_id = self.authenticator.obj.id
        user = self.authenticator.user

        if user and user.is_authenticated:
            group_name = f"user_{user.pk}_conversation_{conversation_id}"
        else:
            group_name = f"anonymous_{conversation_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.groups.append(group_name)

    @ws_handler(
        summary="Handle ping requests",
        description="Simple ping-pong for connectivity testing",
    )
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()

    @event_handler
    async def handle_streaming(self, event: StreamingEvent) -> StreamingMessage:
        return StreamingMessage(payload=event.payload)

    @event_handler
    async def handle_complete_streaming(
        self, event: CompleteStreamingEvent
    ) -> CompleteStreamingMessage:
        return CompleteStreamingMessage(payload=event.payload)

    @event_handler
    async def handle_new_assistant_message(
        self, event: NewAssistantMessageEvent
    ) -> NewAssistantMessage:
        return NewAssistantMessage(payload=event.payload)

    @event_handler
    async def handle_error_assistant_event(
        self, event: ErrorEvent
    ) -> AssistantErrorMessage:
        return AssistantErrorMessage(payload=event.payload)
