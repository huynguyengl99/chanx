"""
Reusable handler mixins for chanx consumers.
"""

from typing import Literal

from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.base import BaseMessage


class ExtraRequestMessage(BaseMessage):
    """Extra request message for ws handler mixin."""

    action: Literal["extra_request"] = "extra_request"
    payload: str


class ExtraEventMessage(BaseMessage):
    """Extra event message for event handler mixin."""

    action: Literal["extra_event"] = "extra_event"
    payload: str


class ExtraResponseMessage(BaseMessage):
    """Extra response message returned by handler mixins."""

    action: Literal["extra_response"] = "extra_response"
    payload: str


class ExtraWsHandlerMixin:
    @ws_handler(
        summary="Handle extra request",
        description="Simple extra message",
    )
    async def handle_extra_message(
        self, message: ExtraRequestMessage
    ) -> ExtraResponseMessage:
        # Do something also
        return ExtraResponseMessage(payload=message.payload + " any extra thing")


class ExtraEventHandlerMixin:
    @event_handler(
        summary="Handle extra event",
        description="Simple extra event message",
    )
    async def handle_extra_event(
        self, event: ExtraEventMessage
    ) -> ExtraResponseMessage:
        return ExtraResponseMessage(payload=event.payload + " any extra thing")
