from django.conf import settings
from django.db import models

from django_extensions.db.models import TimeStampedModel, TitleDescriptionModel


class GroupChat(TitleDescriptionModel, TimeStampedModel):
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_groups",
        through="chat.ChatMember",
    )
