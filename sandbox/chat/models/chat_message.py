from typing import TYPE_CHECKING

from django.db import models

from django_stubs_ext.db.models import TypedModelMeta

if TYPE_CHECKING:
    from chat.models import ChatMember, GroupChat  # noqa: F401


class ChatMessage(models.Model):
    group_chat = models.ForeignKey["GroupChat", "GroupChat"](
        "chat.GroupChat", on_delete=models.CASCADE
    )
    sender = models.ForeignKey["ChatMember | None", "ChatMember | None"](
        "chat.ChatMember", on_delete=models.CASCADE, null=True, blank=True
    )

    content = models.TextField[str, str](default="", blank=True)

    class Meta(TypedModelMeta):
        pass
