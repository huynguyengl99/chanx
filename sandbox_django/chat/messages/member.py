from typing import Any, Literal

from chanx.messages.base import BaseMessage


class MemberMessage(BaseMessage):
    action: Literal["member_message"] = "member_message"
    payload: dict[str, Any]
