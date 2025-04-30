from django.db import models

from django_stubs_ext.db.models import TypedModelMeta


class ChatMessage(models.Model):
    group_chat = models.ForeignKey("chat.GroupChat", on_delete=models.CASCADE)
    sender = models.ForeignKey(
        "chat.ChatMember", on_delete=models.CASCADE, null=True, blank=True
    )

    content = models.TextField(default="", blank=True)

    class Meta(TypedModelMeta):
        pass
