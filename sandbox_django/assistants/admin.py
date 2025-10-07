from typing import Any, ClassVar

from django.contrib import admin
from django.db import models
from django.forms import Textarea

from assistants.constants import MAX_CONTENT_PREVIEW_LENGTH
from assistants.models import AssistantConversation, AssistantMessage


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin[AssistantConversation]):
    list_display = (
        "id",
        "user",
        "title",
        "message_count_display",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)

    def message_count_display(
        self, obj: AssistantConversation
    ) -> int:  # pragma: no cover
        return obj.messages.count()

    # Type ignore for Django admin method attributes
    message_count_display.short_description = "Messages"  # type: ignore[attr-defined]


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin[AssistantMessage]):
    list_display = (
        "id",
        "conversation",
        "message_type",
        "content_preview",
        "created_at",
    )
    list_filter = ("message_type", "created_at")
    search_fields = ("content", "conversation__user__email", "conversation__title")
    readonly_fields = ("created_at",)
    raw_id_fields = ("conversation",)

    fieldsets = (
        (None, {"fields": ("conversation", "message_type", "content")}),
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    # Use ClassVar to explicitly mark as class variable for both mypy and pyright
    formfield_overrides: ClassVar[
        dict[type[models.Field[Any, Any]], dict[str, Any]]
    ] = {
        models.TextField: {"widget": Textarea(attrs={"rows": 6, "cols": 80})},
    }

    def content_preview(self, obj: AssistantMessage) -> str:  # pragma: no cover
        return (
            obj.content[:MAX_CONTENT_PREVIEW_LENGTH] + "..."
            if len(obj.content) > MAX_CONTENT_PREVIEW_LENGTH
            else obj.content
        )

    # Type ignore for Django admin method attributes
    content_preview.short_description = "Content Preview"  # type: ignore[attr-defined]
