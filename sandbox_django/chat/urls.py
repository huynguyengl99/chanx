from django.urls import include, path
from rest_framework.routers import SimpleRouter

from rest_framework_nested import routers

from chat.views import (
    ChatMessageViewSet,
    GroupChatViewSet,
)

# Main router for group chats API
chat_router = SimpleRouter()
chat_router.register(r"", GroupChatViewSet)

# Nested router for messages within a group chat
chat_messages_router = routers.NestedSimpleRouter(chat_router, r"", lookup="group_chat")
chat_messages_router.register(r"messages", ChatMessageViewSet, basename="chat-messages")


# API endpoints
urlpatterns = [
    path("", include(chat_router.urls)),
    path("", include(chat_messages_router.urls)),
]
