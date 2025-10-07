from django.urls import include, path
from rest_framework.routers import SimpleRouter

from rest_framework_nested import routers

from assistants.views.anonymous_conversation_view import create_anonymous_conversation
from assistants.views.conversation_views import AssistantConversationViewSet
from assistants.views.message_views import AssistantMessageViewSet

# Main router for conversations (authenticated users only)
conversation_router = SimpleRouter()
conversation_router.register(
    r"conversations", AssistantConversationViewSet, basename="assistant-conversations"
)

# Nested router for messages within conversations (both authenticated and anonymous)
conversation_messages_router = routers.NestedSimpleRouter(
    conversation_router, r"conversations", lookup="conversation"
)
conversation_messages_router.register(
    r"messages", AssistantMessageViewSet, basename="conversation-messages"
)

# Anonymous conversation messages router
# This handles: /api/assistants/anonymous/{conversation_id}/messages/
anonymous_messages_router = SimpleRouter()
anonymous_messages_router.register(
    r"messages", AssistantMessageViewSet, basename="anonymous-messages"
)

# API endpoints
urlpatterns = [
    # Authenticated user conversations
    path("", include(conversation_router.urls)),
    path("", include(conversation_messages_router.urls)),
    # Anonymous conversation creation
    path(
        "anonymous/",
        create_anonymous_conversation,
        name="create-anonymous-conversation",
    ),
    # Anonymous conversation messages - format: anonymous/{conversation_id}/messages/
    path("anonymous/<uuid:conversation_pk>/", include(anonymous_messages_router.urls)),
]
