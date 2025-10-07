from django.urls import path

from discussion.views import (
    DiscussionHomeView,
    DiscussionTopicDetailView,
    NewDiscussionTopicView,
)

# Web UI routes - nested under /discussion/
urlpatterns = [
    path("", DiscussionHomeView.as_view(), name="discussion-home"),
    path("new/", NewDiscussionTopicView.as_view(), name="discussion-new"),
    path("<int:pk>/", DiscussionTopicDetailView.as_view(), name="discussion-detail"),
]
