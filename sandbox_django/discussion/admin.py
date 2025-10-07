from typing import Any, ClassVar

from django.contrib import admin
from django.db import models
from django.forms import Textarea

from discussion.models import DiscussionReply, DiscussionTopic


@admin.register(DiscussionTopic)
class DiscussionTopicAdmin(admin.ModelAdmin[DiscussionTopic]):
    list_display = (
        "id",
        "title",
        "author",
        "vote_count",
        "reply_count_display",
        "view_count",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("title", "content", "author__email")
    readonly_fields = (
        "created_at",
        "updated_at",
        "view_count",
        "vote_count",
    )
    raw_id_fields = ("author", "accepted_answer")

    fieldsets = (
        (None, {"fields": ("title", "content", "author")}),
        ("Status", {"fields": ("accepted_answer",)}),
        (
            "Stats",
            {
                "fields": ("view_count", "vote_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Use ClassVar to explicitly mark as class variable for both mypy and pyright
    formfield_overrides: ClassVar[
        dict[type[models.Field[Any, Any]], dict[str, Any]]
    ] = {
        models.TextField: {"widget": Textarea(attrs={"rows": 6, "cols": 80})},
    }

    def reply_count_display(self, obj: DiscussionTopic) -> int:  # pragma: no cover
        return obj.reply_count

    # Type ignore for Django admin method attributes
    reply_count_display.short_description = "Replies"  # type: ignore[attr-defined]


@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin[DiscussionReply]):
    list_display = (
        "id",
        "topic_title",
        "author",
        "vote_count",
        "is_accepted_display",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("content", "author__email", "topic__title")
    readonly_fields = (
        "created_at",
        "updated_at",
        "vote_count",
        "is_accepted_display",
    )
    raw_id_fields = ("topic", "author")

    fieldsets = (
        (None, {"fields": ("topic", "author", "content")}),
        ("Status", {"fields": ("is_accepted_display",)}),
        (
            "Stats",
            {"fields": ("vote_count",), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    # Use ClassVar to explicitly mark as class variable for both mypy and pyright
    formfield_overrides: ClassVar[
        dict[type[models.Field[Any, Any]], dict[str, Any]]
    ] = {
        models.TextField: {"widget": Textarea(attrs={"rows": 6, "cols": 80})},
    }

    def topic_title(self, obj: DiscussionReply) -> str:  # pragma: no cover
        return obj.topic.title

    def is_accepted_display(self, obj: DiscussionReply) -> bool:  # pragma: no cover
        return obj.is_accepted

    # Type ignore for Django admin method attributes
    topic_title.short_description = "Topic"  # type: ignore[attr-defined]
    is_accepted_display.short_description = "Accepted"  # type: ignore[attr-defined]
    is_accepted_display.boolean = True  # type: ignore[attr-defined]
