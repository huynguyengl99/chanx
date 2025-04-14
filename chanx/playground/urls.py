from django.urls import path

from .views import WebSocketInfoView, WebSocketPlaygroundView

urlpatterns = [
    path("websocket/", WebSocketPlaygroundView.as_view(), name="websocket_playground"),
    path("websocket-info/", WebSocketInfoView.as_view(), name="websocket_info"),
]
