from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models

from django_stubs_ext.db.models import TypedModelMeta

if TYPE_CHECKING:  # pragma: no cover
    from accounts.models import User  # noqa: F401

    from discussion.models import DiscussionTopic  # noqa: F401


class DiscussionReply(models.Model):
    """A reply/answer to a discussion topic."""

    topic = models.ForeignKey["DiscussionTopic", "DiscussionTopic"](
        "discussion.DiscussionTopic", on_delete=models.CASCADE, related_name="replies"
    )
    author = models.ForeignKey["User", "User"](
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_replies",
    )
    content = models.TextField[str, str]()

    # Simplified: Just track one vote count instead of separate up/down
    vote_count = models.IntegerField[int, int](default=0)

    # Simplified: Remove is_edited flag

    # Timestamps
    created_at = models.DateTimeField[datetime, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime, datetime](auto_now=True)

    class Meta(TypedModelMeta):
        ordering = ["-vote_count", "created_at"]

    @property
    def is_accepted(self) -> bool:
        """Check if this reply is the accepted answer for the topic."""
        return (
            self.topic.accepted_answer is not None
            and self.topic.accepted_answer.pk == self.pk
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to update topic's last activity."""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.topic.update_last_activity()
