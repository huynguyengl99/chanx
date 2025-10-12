"""Tests for FastAPI utility functions."""

from typing import cast
from unittest.mock import Mock

from chanx.fast_channels.type_defs import AsyncAPIConfig
from chanx.fast_channels.utils import build_default_config_from_app, merge_configs
from starlette.requests import Request


class TestBuildDefaultConfigFromApp:
    """Test building default config from FastAPI app."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.mock_request.url.hostname = "localhost"
        self.mock_request.url.scheme = "http"

    def test_build_config_with_basic_app(self) -> None:
        """Test building config from basic app without attributes."""
        mock_app = Mock()
        mock_app.title = None
        mock_app.version = None
        mock_app.description = None

        config = build_default_config_from_app(self.mock_request, mock_app)

        assert config.get("server_url") == "localhost"
        assert config.get("server_protocol") == "ws"
        # Should use defaults for missing attributes
        assert "title" in config
        assert "version" in config
        assert "description" in config

    def test_build_config_with_fastapi_attributes(self) -> None:
        """Test building config from FastAPI app with attributes."""
        mock_app = Mock()
        mock_app.title = "My API"
        mock_app.version = "2.0.0"
        mock_app.description = "API description"

        config = build_default_config_from_app(self.mock_request, mock_app)

        assert config.get("title") == "My API AsyncAPI documentation"
        assert config.get("version") == "2.0.0"
        assert config.get("description") == "API description"
        assert config.get("server_url") == "localhost"
        assert config.get("server_protocol") == "ws"

    def test_build_config_https_request(self) -> None:
        """Test building config with HTTPS request."""
        self.mock_request.url.scheme = "https"
        mock_app = Mock()
        mock_app.title = "Secure API"

        config = build_default_config_from_app(self.mock_request, mock_app)

        assert config.get("server_protocol") == "wss"
        assert config.get("title") == "Secure API AsyncAPI documentation"

    def test_build_config_missing_attributes(self) -> None:
        """Test building config when app is missing some attributes."""
        mock_app = Mock()
        mock_app.title = "Partial API"
        # version and description not set
        mock_app.version = None
        mock_app.description = None

        config = build_default_config_from_app(self.mock_request, mock_app)

        assert config.get("title") == "Partial API AsyncAPI documentation"
        # Should use defaults for missing attributes
        assert "version" in config
        assert "description" in config

    def test_build_config_empty_attributes(self) -> None:
        """Test building config when app has empty string attributes."""
        mock_app = Mock()
        mock_app.title = ""
        mock_app.version = ""
        mock_app.description = ""

        config = build_default_config_from_app(self.mock_request, mock_app)

        # Empty strings are falsy, so should use defaults
        assert "title" in config
        assert "version" in config
        assert "description" in config
        assert config.get("server_url") == "localhost"

    def test_build_config_different_hostname(self) -> None:
        """Test building config with different hostname."""
        self.mock_request.url.hostname = "api.example.com"
        mock_app = Mock()
        mock_app.title = "External API"

        config = build_default_config_from_app(self.mock_request, mock_app)

        assert config.get("server_url") == "api.example.com"
        assert config.get("title") == "External API AsyncAPI documentation"


class TestMergeConfigs:
    """Test configuration merging."""

    def test_merge_with_none_user_config(self) -> None:
        """Test merging when user config is None."""
        base_config = cast(
            AsyncAPIConfig,
            {
                "title": "Base API",
                "version": "1.0.0",
                "server_url": "localhost",
            },
        )

        result = merge_configs(base_config, None)

        assert result == base_config
        assert result is base_config  # Should return the same object

    def test_merge_with_empty_user_config(self) -> None:
        """Test merging with empty user config."""
        base_config = cast(
            AsyncAPIConfig,
            {
                "title": "Base API",
                "version": "1.0.0",
                "server_url": "localhost",
            },
        )
        user_config = cast(AsyncAPIConfig, {})

        result = merge_configs(base_config, user_config)

        assert result == base_config

    def test_merge_with_user_overrides(self) -> None:
        """Test merging with user config overrides."""
        base_config = cast(
            AsyncAPIConfig,
            {
                "title": "Base API",
                "version": "1.0.0",
                "server_url": "localhost",
                "server_protocol": "ws",
            },
        )
        user_config = cast(
            AsyncAPIConfig,
            {
                "title": "Custom API",
                "description": "Custom description",
            },
        )

        result = merge_configs(base_config, user_config)

        expected = {
            "title": "Custom API",  # Overridden
            "version": "1.0.0",  # From base
            "server_url": "localhost",  # From base
            "server_protocol": "ws",  # From base
            "description": "Custom description",  # Added
        }

        assert result == expected

    def test_merge_complete_override(self) -> None:
        """Test merging where user config overrides all base values."""
        base_config = cast(
            AsyncAPIConfig,
            {
                "title": "Base API",
                "version": "1.0.0",
                "server_url": "localhost",
            },
        )
        user_config = cast(
            AsyncAPIConfig,
            {
                "title": "User API",
                "version": "2.0.0",
                "server_url": "api.example.com",
                "description": "User description",
                "server_protocol": "wss",
            },
        )

        result = merge_configs(base_config, user_config)

        expected = {
            "title": "User API",
            "version": "2.0.0",
            "server_url": "api.example.com",
            "description": "User description",
            "server_protocol": "wss",
        }

        assert result == expected

    def test_merge_preserves_base_config(self) -> None:
        """Test that merging doesn't modify the original base config."""
        base_config = cast(
            AsyncAPIConfig,
            {
                "title": "Base API",
                "version": "1.0.0",
            },
        )
        user_config = cast(
            AsyncAPIConfig,
            {
                "title": "Modified API",
            },
        )

        original_base = dict(base_config)
        result = merge_configs(base_config, user_config)

        # Base config should be unchanged
        assert base_config == original_base
        assert result.get("title") == "Modified API"
