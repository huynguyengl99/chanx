from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.db import models

from django_stubs_ext.db.models import TypedModelMeta

if TYPE_CHECKING:  # pragma: no cover
    from chat.models import ChatMember, GroupChat  # noqa: F401


class ChatMessage(models.Model):
    group_chat = models.ForeignKey["GroupChat", "GroupChat"](
        "chat.GroupChat", on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey["ChatMember | None", "ChatMember | None"](
        "chat.ChatMember",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sent_messages",
    )

    content = models.TextField[str, str](default="", blank=True)
    created_at = models.DateTimeField[datetime, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime, datetime](auto_now=True)
    is_edited = models.BooleanField[bool, bool](default=False)

    class Meta(TypedModelMeta):
        ordering = ["-created_at"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to update group chat last activity."""
        is_new = self.pk is None

        super().save(*args, **kwargs)

        # Update group chat last activity timestamp if new message
        if is_new:
            self.group_chat.update_last_activity()
