from unittest import mock
from unittest.mock import ANY

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from chanx.playground.views import WebSocketPlaygroundView


class TestWebSocketPlaygroundView(TestCase):
    """Tests for the WebSocket playground template view."""

    def test_get_context_data(self):
        """Test that the correct context is provided to the template."""
        # Create an instance of the view
        view = WebSocketPlaygroundView()

        # Set up request in the view (normally done by the dispatch method)
        view.request = mock.Mock()
        view.args = []
        view.kwargs = {}

        # Get the context data
        context = view.get_context_data()

        # Verify the websocket_info_url is in the context
        assert "websocket_info_url" in context
        assert context["websocket_info_url"] == reverse("websocket_info")

    def test_template_used(self):
        """Test that the correct template is used."""
        # Use the Django test client to get the view
        response = self.client.get(reverse("websocket_playground"))

        # Check the response is successful
        assert response.status_code == 200

        # Check the correct template was used
        self.assertTemplateUsed(response, "playground/websocket.html")


class TestWebSocketInfoView(APITestCase):
    """Tests for the WebSocket info API view."""

    def setUp(self):
        """Set up for each test method."""
        self.url = reverse("websocket_info")

    def test_get_success(self):
        """Test successful retrieval of WebSocket routes."""

        # Make the API request
        response = self.client.get(self.url)

        # Check the response status and data
        assert response.status_code == 200
        assert response.data == [
            {
                "name": "AssistantConsumer",
                "url": "ws://testserver/ws/assistants/",
                "friendly_url": "ws://testserver/ws/assistants/",
                "description": (
                    "Websocket to chat with server, like chat with chatbot system"
                ),
                "message_examples": [
                    {
                        "name": "NewMessage",
                        "description": "Base websocket message",
                        "example": {
                            "action": "new_message",
                            "payload": {"content": ANY},
                        },
                    },
                    {
                        "name": "PingMessage",
                        "description": (
                            "Simple ping message to check connection status."
                        ),
                        "example": {"action": "ping", "payload": None},
                    },
                ],
                "path_params": [],
            },
            {
                "name": "ChatDetailConsumer",
                "url": "ws://testserver/ws/chat/(?P<pk>\\d+)/",
                "friendly_url": "ws://testserver/ws/chat/:pk/",
                "description": "",
                "message_examples": [
                    {
                        "name": "NewChatMessage",
                        "description": "Base websocket message",
                        "example": {
                            "action": "new_chat_message",
                            "payload": {"content": ANY},
                        },
                    },
                    {
                        "name": "PingMessage",
                        "description": (
                            "Simple ping message to check connection status."
                        ),
                        "example": {"action": "ping", "payload": None},
                    },
                ],
                "path_params": [
                    {
                        "name": "pk",
                        "pattern": "\\d+",
                        "description": "Path parameter: pk",
                    }
                ],
            },
        ]

    @mock.patch("chanx.playground.views.get_playground_websocket_routes")
    def test_get_error(self, mock_get_routes):
        """Test error handling when retrieving WebSocket routes fails."""
        # Mock the function to raise an exception
        mock_get_routes.side_effect = Exception("Test error")

        # Make the API request
        response = self.client.get(self.url)

        # Check the error response
        assert response.status_code == 500
        assert "error" in response.data
        assert "detail" in response.data
        assert response.data["error"] == "Failed to retrieve WebSocket routes"
        assert response.data["detail"] == "Test error"

    @mock.patch("chanx.playground.utils._get_handler_info")
    def test_get_error_deeper_level(self, mock_get_handler_info):
        """Test error handling when retrieving WebSocket routes fails."""
        # Mock the function to raise an exception
        mock_get_handler_info.side_effect = TypeError("Type error")

        # Make the API request
        response = self.client.get(self.url)

        # Check the error response
        assert response.status_code == 500
        assert "error" in response.data
        assert "detail" in response.data
        assert response.data["error"] == "Failed to retrieve WebSocket routes"
        assert response.data["detail"] == "Type error"
