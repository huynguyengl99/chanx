import typing

from django.conf import settings
from django.db import models

from django_stubs_ext.db.models import TypedModelMeta

if typing.TYPE_CHECKING:  # pragma: no cover
    from accounts.models import User  # noqa: F401

    from chat.models import GroupChat  # noqa: F401


class ChatMember(models.Model):
    class ChatMemberRole(models.IntegerChoices):
        OWNER = 2001
        ADMIN = 2002
        MEMBER = 2003

    chat_role = models.IntegerField[int, int](
        choices=ChatMemberRole.choices,
        default=ChatMemberRole.MEMBER,
        help_text="Chat member roles prefix with 2xxx",
    )
    group_chat = models.ForeignKey["GroupChat", "GroupChat"](
        "chat.GroupChat", on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey["User", "User"](
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="members"
    )

    nick_name = models.CharField[str, str](default="", blank=True)

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "user", "group_chat", name="unique_sender_in_group"
            ),
        ]
