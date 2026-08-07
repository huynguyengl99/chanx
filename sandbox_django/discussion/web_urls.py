from django.urls import path

from discussion.views import (
    DiscussionHomeView,
    DiscussionMultiplexView,
    DiscussionTopicDetailView,
    NewDiscussionTopicView,
)

# Web UI routes - nested under /discussion/
urlpatterns = [
    path("", DiscussionHomeView.as_view(), name="discussion-home"),
    path("new/", NewDiscussionTopicView.as_view(), name="discussion-new"),
    path("mux/", DiscussionMultiplexView.as_view(), name="discussion-mux"),
    path("<int:pk>/", DiscussionTopicDetailView.as_view(), name="discussion-detail"),
]
