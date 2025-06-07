from typing import Any, Literal

from chanx.messages.base import BaseGroupMessage


class MemberMessage(BaseGroupMessage):
    action: Literal["member_message"] = "member_message"
    payload: dict[str, Any]
