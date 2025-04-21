"""
URL configuration for the Chanx Playground.

This module defines the URL patterns for the WebSocket debugging and exploration
tools provided by Chanx. The playground offers a visual interface for exploring
available WebSocket endpoints, testing connections, and sending/receiving messages.

URLs:
- /websocket/: WebSocket playground UI for interactive testing
- /websocket-info/: API endpoint providing WebSocket route information
"""

from django.urls import path

from .views import WebSocketInfoView, WebSocketPlaygroundView

urlpatterns = [
    path("websocket/", WebSocketPlaygroundView.as_view(), name="websocket_playground"),
    path("websocket-info/", WebSocketInfoView.as_view(), name="websocket_info"),
]
