"""Tests for FastAPI AsyncAPI view functions."""

import json
from typing import cast
from unittest.mock import Mock, patch

import pytest
from chanx.fast_channels.type_defs import AsyncAPIConfig
from chanx.fast_channels.views import (
    asyncapi_docs,
    asyncapi_spec_json,
    asyncapi_spec_yaml,
    generate_asyncapi_schema,
)
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket


class TestGenerateAsyncAPISchema:
    """Test AsyncAPI schema generation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.mock_request.url.netloc = "localhost"
        self.mock_request.url.scheme = "http"

        async def websocket_endpoint(websocket: WebSocket) -> None:
            pass

        self.app = FastAPI(
            routes=[
                WebSocketRoute("/ws", websocket_endpoint),
            ]
        )
        # Add FastAPI-like attributes
        self.app.title = "Test API"
        self.app.version = "1.0.0"
        self.app.description = "Test description"

    def test_generate_schema_basic(self) -> None:
        """Test that config is built correctly and passed to generator."""
        # This tests the view logic: config building and generator invocation
        with patch(
            "chanx.fast_channels.views.AsyncAPIGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = {"asyncapi": "3.0.0"}
            mock_generator_class.return_value = mock_generator

            result = generate_asyncapi_schema(self.mock_request, self.app)

            # Verify the generator was called with correct config from app
            mock_generator_class.assert_called_once()
            call_kwargs = mock_generator_class.call_args[1]

            assert call_kwargs["title"] == "Test API AsyncAPI documentation"
            assert call_kwargs["version"] == "1.0.0"
            assert call_kwargs["description"] == "Test description"
            assert call_kwargs["server_url"] == "localhost"
            assert call_kwargs["server_protocol"] == "ws"

            assert result == {"asyncapi": "3.0.0"}

    def test_generate_schema_with_config(self) -> None:
        """Test that custom config overrides app defaults correctly."""
        custom_config = cast(
            AsyncAPIConfig, {"title": "Custom API Title", "version": "2.0.0"}
        )

        with patch(
            "chanx.fast_channels.views.AsyncAPIGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = {"asyncapi": "3.0.0"}
            mock_generator_class.return_value = mock_generator

            generate_asyncapi_schema(self.mock_request, self.app, custom_config)

            # Verify custom config overrides work
            call_kwargs = mock_generator_class.call_args[1]
            assert call_kwargs["title"] == "Custom API Title"  # Overridden
            assert call_kwargs["version"] == "2.0.0"  # Overridden
            assert call_kwargs["description"] == "Test description"  # From app

    def test_generate_schema_without_camelize(self) -> None:
        """Test that camelize defaults to False when not specified."""
        with patch(
            "chanx.fast_channels.views.AsyncAPIGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = {"asyncapi": "3.0.0"}
            mock_generator_class.return_value = mock_generator

            generate_asyncapi_schema(self.mock_request, self.app)

            # Verify camelize defaults to False
            call_kwargs = mock_generator_class.call_args[1]
            assert call_kwargs["camelize"] is False

    def test_generate_schema_with_camelize_true(self) -> None:
        """Test that camelize=True is passed to generator."""
        custom_config = cast(AsyncAPIConfig, {"camelize": True})

        with patch(
            "chanx.fast_channels.views.AsyncAPIGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = {"asyncapi": "3.0.0"}
            mock_generator_class.return_value = mock_generator

            generate_asyncapi_schema(self.mock_request, self.app, custom_config)

            # Verify camelize is passed as True
            call_kwargs = mock_generator_class.call_args[1]
            assert call_kwargs["camelize"] is True

    def test_generate_schema_with_camelize_false(self) -> None:
        """Test that camelize=False is passed to generator."""
        custom_config = cast(AsyncAPIConfig, {"camelize": False})

        with patch(
            "chanx.fast_channels.views.AsyncAPIGenerator"
        ) as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate.return_value = {"asyncapi": "3.0.0"}
            mock_generator_class.return_value = mock_generator

            generate_asyncapi_schema(self.mock_request, self.app, custom_config)

            # Verify camelize is passed as False
            call_kwargs = mock_generator_class.call_args[1]
            assert call_kwargs["camelize"] is False


class TestAsyncAPISpecJSON:
    """Test JSON spec endpoint."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.app = FastAPI()
        # Add FastAPI-like attributes
        self.app.title = "Test API"
        self.app.version = "1.0.0"
        self.app.description = "Test description"

    @pytest.mark.asyncio
    async def test_successful_json_response(self) -> None:
        """Test successful JSON spec generation."""
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Test API"}}

        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.return_value = expected_schema

            response = await asyncapi_spec_json(self.mock_request, self.app)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 200

            response_data = json.loads(bytes(response.body).decode())
            assert response_data == expected_schema

    @pytest.mark.asyncio
    async def test_json_response_with_config(self) -> None:
        """Test JSON spec generation with custom config."""
        config = cast(AsyncAPIConfig, {"title": "Custom API Title"})
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Custom API Title"}}

        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.return_value = expected_schema

            response = await asyncapi_spec_json(self.mock_request, self.app, config)

            assert isinstance(response, JSONResponse)
            response_data = json.loads(bytes(response.body).decode())
            assert response_data == expected_schema

            # Verify config was passed correctly
            mock_generate.assert_called_once_with(
                request=self.mock_request, app=self.app, config=config
            )

    @pytest.mark.asyncio
    async def test_json_response_error_handling(self) -> None:
        """Test error handling in JSON spec generation."""
        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.side_effect = Exception("Test error")

            response = await asyncapi_spec_json(self.mock_request, self.app)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

            response_data = json.loads(bytes(response.body).decode())
            assert "error" in response_data
            assert "Test error" in response_data["error"]


class TestAsyncAPISpecYAML:
    """Test YAML spec endpoint."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.app = FastAPI()
        # Add FastAPI-like attributes
        self.app.title = "Test API"
        self.app.version = "1.0.0"
        self.app.description = "Test description"

    @pytest.mark.asyncio
    async def test_yaml_not_available(self) -> None:
        """Test YAML response when PyYAML is not available."""
        with patch("chanx.fast_channels.views.yaml_available", False):
            response = await asyncapi_spec_yaml(self.mock_request, self.app)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 400

            response_data = json.loads(bytes(response.body).decode())
            assert "error" in response_data
            assert "PyYAML" in response_data["error"]

    @pytest.mark.asyncio
    async def test_successful_yaml_response(self) -> None:
        """Test successful YAML spec generation."""
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Test API"}}

        with (
            patch("chanx.fast_channels.views.yaml_available", True),
            patch(
                "chanx.fast_channels.views.generate_asyncapi_schema"
            ) as mock_generate,
        ):

            mock_generate.return_value = expected_schema

            response = await asyncapi_spec_yaml(self.mock_request, self.app)

            assert isinstance(response, Response)
            assert response.media_type == "application/x-yaml"

            # Verify it contains the schema data as YAML
            yaml_content = bytes(response.body).decode()
            assert "asyncapi: 3.0.0" in yaml_content
            assert "Test API" in yaml_content

    @pytest.mark.asyncio
    async def test_yaml_response_with_config(self) -> None:
        """Test YAML spec generation with custom config."""
        config = cast(AsyncAPIConfig, {"title": "Custom YAML API"})
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Custom YAML API"}}

        with (
            patch("chanx.fast_channels.views.yaml_available", True),
            patch(
                "chanx.fast_channels.views.generate_asyncapi_schema"
            ) as mock_generate,
        ):

            mock_generate.return_value = expected_schema
            response = await asyncapi_spec_yaml(self.mock_request, self.app, config)

            yaml_content = bytes(response.body).decode()
            assert "Custom YAML API" in yaml_content

    @pytest.mark.asyncio
    async def test_yaml_response_error_handling(self) -> None:
        """Test error handling in YAML spec generation."""
        mock_yaml = Mock()

        with (
            patch("chanx.fast_channels.views.yaml_available", True),
            patch("chanx.fast_channels.views.yaml", mock_yaml),
            patch(
                "chanx.fast_channels.views.generate_asyncapi_schema"
            ) as mock_generate,
        ):

            mock_generate.side_effect = Exception("Test error")

            response = await asyncapi_spec_yaml(self.mock_request, self.app)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

            response_data = json.loads(bytes(response.body).decode())
            assert "error" in response_data
            assert "Test error" in response_data["error"]


class TestAsyncAPIDocs:
    """Test AsyncAPI documentation endpoint."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.app = FastAPI()
        # Add FastAPI-like attributes
        self.app.title = "Test API"
        self.app.version = "1.0.0"
        self.app.description = "Test description"

    @pytest.mark.asyncio
    async def test_successful_docs_response(self) -> None:
        """Test successful docs generation."""
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Test API"}}

        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.return_value = expected_schema

            response = await asyncapi_docs(self.mock_request, self.app)

            assert isinstance(response, HTMLResponse)
            assert response.status_code == 200

            html_content = bytes(response.body).decode()
            assert "Test API" in html_content
            assert "AsyncApiStandalone.render" in html_content

    @pytest.mark.asyncio
    async def test_docs_response_with_config(self) -> None:
        """Test docs generation with custom config."""
        config = cast(AsyncAPIConfig, {"title": "Custom Docs API"})
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Custom Docs API"}}

        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.return_value = expected_schema

            response = await asyncapi_docs(self.mock_request, self.app, config)

            html_content = bytes(response.body).decode()
            assert "Custom Docs API" in html_content

    @pytest.mark.asyncio
    async def test_docs_response_error_handling(self) -> None:
        """Test error handling in docs generation."""
        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.side_effect = Exception("Test error")

            response = await asyncapi_docs(self.mock_request, self.app)

            assert isinstance(response, HTMLResponse)
            assert response.status_code == 500

            html_content = bytes(response.body).decode()
            assert "Error" in html_content
            assert "Test error" in html_content

    @pytest.mark.asyncio
    async def test_docs_html_structure(self) -> None:
        """Test that the generated HTML has the correct structure."""
        expected_schema = {"asyncapi": "3.0.0", "info": {"title": "Test API"}}

        with patch(
            "chanx.fast_channels.views.generate_asyncapi_schema"
        ) as mock_generate:
            mock_generate.return_value = expected_schema

            response = await asyncapi_docs(self.mock_request, self.app)

            html_content = bytes(response.body).decode()

            # Check HTML structure
            assert "<!DOCTYPE html>" in html_content
            assert "<html>" in html_content
            assert "<head>" in html_content
            assert "<body>" in html_content
            assert 'id="asyncapi"' in html_content

            # Check AsyncAPI React component
            assert "@asyncapi/react-component" in html_content
            assert "AsyncApiStandalone.render" in html_content
