from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.db.models import QuerySet

from django_stubs_ext.db.models import TypedModelMeta

if TYPE_CHECKING:  # pragma: no cover
    from accounts.models import User  # noqa: F401

    from discussion.models import DiscussionReply  # noqa: F401


class DiscussionTopic(models.Model):
    """A discussion topic/thread."""

    title = models.CharField[str, str](max_length=200)
    content = models.TextField[str, str]()
    author = models.ForeignKey["User", "User"](
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_topics",
    )

    # Simplified: Just track one vote count instead of separate up/down
    vote_count = models.IntegerField[int, int](default=0)

    # Status
    view_count = models.IntegerField[int, int](default=0)

    # Simplified: Remove is_pinned and is_locked flags

    # Timestamps
    created_at = models.DateTimeField[datetime, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime, datetime](auto_now=True)

    # For tracking the accepted answer
    accepted_answer = models.ForeignKey[
        "DiscussionReply | None", "DiscussionReply | None"
    ](
        "discussion.DiscussionReply",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_for_topic",
    )

    if TYPE_CHECKING:  # pragma: no cover
        # Annotate reverse relationships for type checking
        replies: QuerySet["DiscussionReply"]

    class Meta(TypedModelMeta):
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return self.title

    @property
    def reply_count(self) -> int:
        """Total number of replies (answers)."""
        return self.replies.count()

    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.save(update_fields=["updated_at"])
