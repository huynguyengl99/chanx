"""
Helper module with `from __future__ import annotations` enabled.

Used to test that decorators work correctly when annotations are stringified.
"""

from __future__ import annotations

from typing import Any, Literal

from chanx.core.decorators import event_handler, ws_handler
from chanx.messages.base import BaseMessage


class FutureMessage(BaseMessage):
    action: Literal["future_test"] = "future_test"
    payload: dict[str, Any]


class FutureResponse(BaseMessage):
    action: Literal["future_response"] = "future_response"
    payload: str


@ws_handler
async def handle_future(self: Any, message: FutureMessage) -> FutureResponse:
    return FutureResponse(payload="handled")


@ws_handler(action="custom_future")
async def handle_future_custom(self: Any, message: FutureMessage) -> FutureResponse:
    return FutureResponse(payload="custom")


@event_handler
async def handle_future_event(self: Any, event: FutureMessage) -> None:
    pass
