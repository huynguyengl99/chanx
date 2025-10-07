from django.urls import include, path
from rest_framework.routers import SimpleRouter

from rest_framework_nested import routers

from discussion.views import DiscussionReplyViewSet, DiscussionTopicViewSet

# Main router for discussion topics API
discussion_router = SimpleRouter()
discussion_router.register(r"", DiscussionTopicViewSet, basename="discussion-topic")

# Nested router for replies within a topic
discussion_replies_router = routers.NestedSimpleRouter(
    discussion_router, r"", lookup="topic"
)
discussion_replies_router.register(
    r"replies", DiscussionReplyViewSet, basename="discussion-reply"
)

# API endpoints
urlpatterns = [
    path("", include(discussion_router.urls)),
    path("", include(discussion_replies_router.urls)),
]
