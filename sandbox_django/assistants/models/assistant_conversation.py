from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import QuerySet

import structlog
from django_stubs_ext.db.models import TypedModelMeta

from assistants.constants import TRUNCATED_TITLE_LENGTH

if TYPE_CHECKING:  # pragma: no cover
    from accounts.models import User  # noqa: F401

    from assistants.models.assistant_message import AssistantMessage  # noqa: F401

logger = structlog.getLogger(__name__)


class AssistantConversation(models.Model):
    """A conversation thread with the AI assistant."""

    id = models.UUIDField[str, str](primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey["User | None", "User | None"](
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_conversations",
        null=True,  # Allow anonymous conversations
        blank=True,
    )
    title = models.CharField[str, str](max_length=200, blank=True)
    created_at = models.DateTimeField[datetime, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime, datetime](auto_now=True)

    # Type annotation for reverse relationship
    if TYPE_CHECKING:  # pragma: no cover
        messages: QuerySet["AssistantMessage"]

    class Meta(TypedModelMeta):
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        user_info = f" ({self.user.email})" if self.user else " (anonymous)"
        return f"Conversation {self.id} - {self.title or 'Untitled'}{user_info}"

    def generate_title_from_first_message(self) -> None:
        """Generate a title from the first user message if not already set."""
        if not self.title:
            from assistants.models.assistant_message import AssistantMessage

            first_message = self.messages.filter(
                message_type=AssistantMessage.MessageType.USER
            ).first()

            assert first_message is not None
            from assistants.tasks.ai_service_tasks import (
                task_generate_conversation_title,
            )

            try:
                generated_title = task_generate_conversation_title(
                    first_message.content
                )
                self.title = generated_title
                self.save(update_fields=["title"])

            except Exception:
                # Fallback to simple truncation
                logger.exception("Failed to generate title")
                self.title = first_message.content[:TRUNCATED_TITLE_LENGTH]
                if len(first_message.content) > TRUNCATED_TITLE_LENGTH:
                    self.title += "..."
                self.save(update_fields=["title"])
