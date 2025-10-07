from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.db import models

from django_stubs_ext.db.models import TypedModelMeta

if TYPE_CHECKING:  # pragma: no cover
    from assistants.models.assistant_conversation import (
        AssistantConversation,  # noqa: F401
    )


class AssistantMessage(models.Model):
    """A message in an assistant conversation."""

    class MessageType(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey["AssistantConversation", "AssistantConversation"](
        "assistants.AssistantConversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    content = models.TextField[str, str]()
    message_type = models.CharField[str, str](
        max_length=10, choices=MessageType.choices, default=MessageType.USER
    )
    created_at = models.DateTimeField[datetime, datetime](auto_now_add=True)

    class Meta(TypedModelMeta):
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.message_type}: {self.content[:50]}..."

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Update conversation timestamp when message is saved."""
        super().save(*args, **kwargs)
        # Update conversation's updated_at timestamp
        self.conversation.save(update_fields=["updated_at"])
