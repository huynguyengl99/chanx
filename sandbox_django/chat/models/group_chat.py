from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet

from django_stubs_ext.db.models import TypedModelMeta

from chat.models import ChatMember

if TYPE_CHECKING:  # pragma: no cover
    from accounts.models import User  # noqa: F401


class GroupChat(models.Model):
    title = models.CharField[str, str](max_length=255)
    description = models.TextField[str | None, str | None](blank=True, null=True)
    users = models.ManyToManyField["User", "User"](
        "accounts.User",
        related_name="chat_groups",
        through="chat.ChatMember",
    )
    created_at = models.DateTimeField[datetime, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime, datetime](auto_now=True)

    members: QuerySet[ChatMember]

    class Meta(TypedModelMeta):
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title

    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.save(update_fields=["updated_at"])
