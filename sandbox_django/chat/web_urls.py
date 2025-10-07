from django.urls import path

from chat.views import (
    GroupChatDetailView,
    GroupMemberManagementView,
    HomeView,
    RemoveMemberView,
)

# Web UI routes - nested under /chat/
urlpatterns = [
    path("", HomeView.as_view(), name="chat-home"),
    path("<int:pk>/", GroupChatDetailView.as_view(), name="chat-group-detail"),
    path(
        "<int:pk>/members/",
        GroupMemberManagementView.as_view(),
        name="group_members",
    ),
    path(
        "<int:pk>/members/<int:member_id>/remove/",
        RemoveMemberView.as_view(),
        name="remove_member",
    ),
]
