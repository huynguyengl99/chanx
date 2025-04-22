from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from chanx.constants import MISSING_PYHUMPS_ERROR
from chanx.playground.views import WebSocketPlaygroundView
from chanx.utils.settings import override_chanx_settings


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
        assert len(response.data) == 3

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

    @override_chanx_settings(CAMELIZE=True)
    def test_websocket_info_with_camelize(self):
        """Test error handling when humps is missing but CAMELIZE is True."""
        response = self.client.get(self.url)

        # Check the response status and data
        assert response.status_code == 200
        assert len(response.data) == 3

    @mock.patch("chanx.playground.utils.humps", None)
    @override_chanx_settings(CAMELIZE=True)
    def test_missing_humps_in_websocket_info_view(self):
        """Test error handling when humps is missing but CAMELIZE is True."""
        response = self.client.get(self.url)

        # Check the error response
        assert response.status_code == 500
        assert "error" in response.data
        assert "detail" in response.data
        assert response.data["error"] == "Failed to retrieve WebSocket routes"
        assert MISSING_PYHUMPS_ERROR in response.data["detail"]
