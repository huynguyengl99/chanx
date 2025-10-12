from unittest.mock import Mock, patch

from django.test import TestCase

from chanx.channels.utils import get_websocket_application


class TestAsgiUtils(TestCase):
    """Test cases for ASGI utility functions."""

    def test_get_websocket_application_success(self) -> None:
        """Test successful retrieval of WebSocket application."""
        # Create a mock application with application_mapping
        mock_ws_app = Mock()
        mock_application = Mock()
        mock_application.application_mapping = {"websocket": mock_ws_app}

        with patch(
            "chanx.channels.utils.asgi.get_default_application",
            return_value=mock_application,
        ):
            result = get_websocket_application()
            assert result == mock_ws_app

    def test_get_websocket_application_no_mapping(self) -> None:
        """Test when application doesn't have application_mapping attribute."""
        # Create a mock application without application_mapping
        mock_application = Mock(spec=[])

        with patch(
            "chanx.channels.utils.asgi.get_default_application",
            return_value=mock_application,
        ):
            result = get_websocket_application()
            assert result is None

    def test_get_websocket_application_no_websocket(self) -> None:
        """Test when application_mapping doesn't contain 'websocket' key."""
        # Create a mock application with application_mapping but no websocket
        mock_application = Mock()
        mock_application.application_mapping = {"http": Mock()}

        with patch(
            "chanx.channels.utils.asgi.get_default_application",
            return_value=mock_application,
        ):
            result = get_websocket_application()
            assert result is None
