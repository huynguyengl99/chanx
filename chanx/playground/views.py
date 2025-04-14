from typing import Any

from django.http import HttpRequest
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from ..utils import logger
from .utils import WebSocketRoute, get_websocket_routes


class WebSocketPlaygroundView(TemplateView):
    """
    A view that renders the WebSocket playground template.
    """

    template_name = "playground/websocket.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # Add the API endpoint URL to the context
        context["websocket_info_url"] = reverse("websocket_info")

        return context


class WebSocketRouteSerializer(serializers.Serializer[WebSocketRoute]):
    """
    Serializer for WebSocket route information.
    """

    name = serializers.CharField()
    url = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    message_examples = serializers.ListField(
        child=serializers.DictField(), required=False
    )


class WebSocketRouteListSerializer(serializers.ListSerializer[list[WebSocketRoute]]):
    """
    List serializer for WebSocket routes.
    """

    child = WebSocketRouteSerializer()


class WebSocketInfoView(APIView):
    """
    API view to provide information about available WebSocket endpoints.
    """

    serializer_class = WebSocketRouteListSerializer

    def get(self, request: HttpRequest) -> Response:
        try:
            # Get available WebSocket endpoints using the utility function
            available_endpoints: list[WebSocketRoute] = get_websocket_routes(request)

            # Use the list serializer directly
            serializer = WebSocketRouteListSerializer(available_endpoints)
            return Response(serializer.data)
        except Exception as e:
            # Return error details for debugging
            logger.exception("Error happened when get websocket info")
            return Response(
                {"error": "Failed to retrieve WebSocket routes", "detail": str(e)},
                status=500,
            )
