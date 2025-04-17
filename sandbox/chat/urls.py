from django.urls import include, path
from rest_framework.routers import SimpleRouter

from chat.views import (
    GroupChatViewSet,
)

chat_router = SimpleRouter()
chat_router.register(r"", GroupChatViewSet)


urlpatterns = [
    path("", include(chat_router.urls)),
]
