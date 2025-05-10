"""
Views for the Chanx WebSocket Playground interface.

This module provides the web interface and API views for the WebSocket playground,
a developer tool for exploring and testing WebSocket endpoints. The playground offers
a visual interface where developers can:

1. Browse available WebSocket endpoints
2. Connect to endpoints and test authentication
3. Send and receive messages with syntax highlighting
4. View message examples and documentation

The module includes both the HTML template view (WebSocketPlaygroundView) for the
interactive interface and the API view (WebSocketInfoView) that provides the WebSocket
route information to the frontend.
"""

from typing import Any

from django.http import HttpRequest
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from chanx.utils.logging import logger

from .utils import WebSocketRoute, get_playground_websocket_routes


class WebSocketPlaygroundView(TemplateView):
    """
    A view that renders the WebSocket playground interface.

    This view provides the main interactive UI for the WebSocket playground,
    enabling developers to browse available WebSocket endpoints, connect to them,
    send/receive messages, and view documentation. The template includes a
    JavaScript application that communicates with the WebSocketInfoView API
    to dynamically load available endpoints.
    """

    template_name = "playground/websocket.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Enhance the template context with WebSocket playground-specific data.

        Adds the WebSocket info API URL to the template context to allow
        the frontend to dynamically load available WebSocket endpoints.

        Args:
            **kwargs: Additional keyword arguments passed to the template

        Returns:
            Enhanced context dictionary with playground-specific variables
        """
        context = super().get_context_data(**kwargs)
        # Add the API endpoint URL to the context
        context["websocket_info_url"] = reverse("websocket_info")

        return context


class WebSocketRouteSerializer(serializers.Serializer[WebSocketRoute]):
    """
    Serializer for WebSocket route information in the playground.

    Converts internal WebSocketRoute TypedDict objects into a format suitable
    for the API response, including endpoint URLs, descriptions, message examples,
    and path parameters that the frontend can use to build a dynamic interface.
    """

    name = serializers.CharField()
    url = serializers.CharField()
    friendly_url = serializers.CharField(allow_blank=True, required=False)
    description = serializers.CharField(allow_blank=True)
    message_examples = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    path_params = serializers.ListField(child=serializers.DictField(), required=False)


class WebSocketRouteListSerializer(serializers.ListSerializer[list[WebSocketRoute]]):
    """
    List serializer for WebSocket routes in the playground API.

    Handles the serialization of multiple WebSocket routes into a consistent
    list format for the frontend to consume. Uses WebSocketRouteSerializer as
    its child serializer.
    """

    child = WebSocketRouteSerializer()


class WebSocketInfoView(APIView):
    """
    API view to provide information about available WebSocket endpoints.
    """

    serializer_class = WebSocketRouteListSerializer
    authentication_classes = []

    def get(self, request: HttpRequest) -> Response:
        """
        Retrieve information about available WebSocket endpoints.

        This method fetches all discoverable WebSocket routes from the application,
        serializes them, and returns a structured response. The response includes
        endpoint URLs, descriptions, message examples, and path parameters for
        each WebSocket consumer.

        Args:
            request: The HTTP request object used to determine the current domain
                    for WebSocket URL construction

        Returns:
            Response with serialized WebSocket route information

        Raises:
            Any exceptions are caught and returned as a 500 error response with details
        """

        try:
            # Get available WebSocket endpoints using the new playground utility function
            available_endpoints: list[WebSocketRoute] = get_playground_websocket_routes(
                request
            )

            # Use the list serializer directly
            return Response(available_endpoints)
        except Exception as e:
            # Return error details for debugging
            logger.exception("Error happened when get websocket info")
            return Response(
                {"error": "Failed to retrieve WebSocket routes", "detail": str(e)},
                status=500,
            )
