from django.conf import settings
from django.db import models

from django_extensions.db.models import TimeStampedModel


class ChatMember(TimeStampedModel):
    class ChatMemberRole(models.IntegerChoices):
        OWNER = 2001
        ADMIN = 2002
        MEMBER = 2003

    chat_role = models.IntegerField(
        choices=ChatMemberRole.choices,
        default=ChatMemberRole.MEMBER,
        help_text="Chat member roles prefix with 2xxx",
    )
    group_chat = models.ForeignKey("chat.GroupChat", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    nick_name = models.CharField(default="", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "user", "group_chat", name="unique_sender_in_group"
            ),
        ]
        ordering = ["-created"]
