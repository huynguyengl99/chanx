from django.db import models

from django_stubs_ext.db.models import TypedModelMeta


class GroupChat(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    users = models.ManyToManyField(
        "accounts.User",
        related_name="chat_groups",
        through="chat.ChatMember",
    )

    class Meta(TypedModelMeta):
        pass
