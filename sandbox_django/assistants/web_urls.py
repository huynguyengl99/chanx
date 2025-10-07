from django.urls import path

from .views import AssistantChatView

urlpatterns = [
    # Root URL - conversation list or welcome page
    path("", AssistantChatView.as_view(), name="assistant_chat"),
    # Specific conversation for both authenticated and anonymous users
    path(
        "<uuid:conversation_id>/",
        AssistantChatView.as_view(),
        name="assistant_conversation",
    ),
]
