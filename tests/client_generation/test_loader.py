"""Tests for SchemaLoader."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
from chanx.client_generator.loader import SchemaLoader


class TestSchemaLoader(TestCase):
    """Test cases for SchemaLoader."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test fixtures."""
        self.tmp_path = tmp_path

    def test_load_json_file(self) -> None:
        """Test loading a JSON schema file."""
        schema_file = self.tmp_path / "schema.json"
        schema_file.write_text('{"asyncapi": "3.0.0", "info": {"title": "Test"}}')

        result = SchemaLoader.load(str(schema_file))

        assert result["asyncapi"] == "3.0.0"
        assert result["info"]["title"] == "Test"

    def test_load_yaml_file(self) -> None:
        """Test loading a YAML schema file."""
        schema_file = self.tmp_path / "schema.yaml"
        schema_file.write_text(
            """
asyncapi: '3.0.0'
info:
  title: Test YAML
  version: 1.0.0
"""
        )

        result = SchemaLoader.load(str(schema_file))

        assert result["asyncapi"] == "3.0.0"
        assert result["info"]["title"] == "Test YAML"

    def test_load_yml_file(self) -> None:
        """Test loading a .yml schema file."""
        schema_file = self.tmp_path / "schema.yml"
        schema_file.write_text("asyncapi: '3.0.0'\ninfo:\n  title: Test\n")

        result = SchemaLoader.load(str(schema_file))

        assert result["asyncapi"] == "3.0.0"

    def test_load_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError, match="Schema file not found"):
            SchemaLoader.load("/nonexistent/schema.json")

    def test_load_invalid_json(self) -> None:
        """Test that ValueError is raised for invalid JSON."""
        schema_file = self.tmp_path / "invalid.json"
        schema_file.write_text("{invalid json}")

        with pytest.raises(ValueError, match="Invalid JSON format"):
            SchemaLoader.load(str(schema_file))

    def test_load_invalid_yaml(self) -> None:
        """Test that ValueError is raised for invalid YAML."""
        schema_file = self.tmp_path / "invalid.yaml"
        schema_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ValueError, match="Invalid YAML format"):
            SchemaLoader.load(str(schema_file))

    def test_load_json_array_not_object(self) -> None:
        """Test that ValueError is raised for JSON array instead of object."""
        schema_file = self.tmp_path / "array.json"
        schema_file.write_text("[1, 2, 3]")

        with pytest.raises(ValueError, match="Schema must be a JSON object"):
            SchemaLoader.load(str(schema_file))

    def test_load_yaml_array_not_object(self) -> None:
        """Test that ValueError is raised for YAML array instead of object."""
        schema_file = self.tmp_path / "array.yaml"
        schema_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError, match="Schema must be a YAML object"):
            SchemaLoader.load(str(schema_file))

    def test_load_auto_detect_json(self) -> None:
        """Test auto-detection of JSON format for files without standard extension."""
        schema_file = self.tmp_path / "schema.txt"
        schema_file.write_text('{"asyncapi": "3.0.0"}')

        result = SchemaLoader.load(str(schema_file))

        assert result["asyncapi"] == "3.0.0"

    def test_load_auto_detect_yaml(self) -> None:
        """Test auto-detection of YAML format for files without standard extension."""
        schema_file = self.tmp_path / "schema.txt"
        schema_file.write_text("asyncapi: '3.0.0'\n")

        result = SchemaLoader.load(str(schema_file))

        assert result["asyncapi"] == "3.0.0"

    def test_load_auto_detect_fails(self) -> None:
        """Test that ValueError is raised when auto-detection fails."""
        schema_file = self.tmp_path / "schema.txt"
        schema_file.write_text("not valid json or yaml")

        with pytest.raises(ValueError, match="Could not parse schema file"):
            SchemaLoader.load(str(schema_file))

    def test_is_url_http(self) -> None:
        """Test URL detection for HTTP URLs."""
        assert SchemaLoader._is_url("http://example.com/schema.json") is True

    def test_is_url_https(self) -> None:
        """Test URL detection for HTTPS URLs."""
        assert SchemaLoader._is_url("https://example.com/schema.json") is True

    def test_is_url_file_path(self) -> None:
        """Test URL detection for file paths."""
        assert SchemaLoader._is_url("/path/to/schema.json") is False
        assert SchemaLoader._is_url("schema.json") is False
        assert SchemaLoader._is_url("./schema.json") is False

    def test_is_url_malformed(self) -> None:
        """Test URL detection for malformed strings."""
        assert SchemaLoader._is_url("not a url") is False
        assert SchemaLoader._is_url("") is False

    def test_load_from_url_json(self) -> None:
        """Test loading schema from URL with JSON content."""
        import sys
        from unittest.mock import MagicMock

        # Mock httpx module
        mock_httpx = MagicMock()
        mock_response = Mock()
        mock_response.text = '{"asyncapi": "3.0.0", "info": {"title": "Test"}}'
        mock_response.headers = {"content-type": "application/json"}
        mock_httpx.get.return_value = mock_response

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = SchemaLoader.load("https://example.com/schema.json")

        assert result["asyncapi"] == "3.0.0"
        assert result["info"]["title"] == "Test"
        mock_httpx.get.assert_called_once_with(
            "https://example.com/schema.json", follow_redirects=True, timeout=30.0
        )

    def test_load_from_url_yaml(self) -> None:
        """Test loading schema from URL with YAML content."""
        import sys
        from unittest.mock import MagicMock

        mock_httpx = MagicMock()
        mock_response = Mock()
        mock_response.text = "asyncapi: '3.0.0'\ninfo:\n  title: Test\n"
        mock_response.headers = {"content-type": "application/x-yaml"}
        mock_httpx.get.return_value = mock_response

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = SchemaLoader.load("https://example.com/schema.yaml")

        assert result["asyncapi"] == "3.0.0"

    def test_load_from_url_json_by_extension(self) -> None:
        """Test loading JSON from URL based on file extension."""
        import sys
        from unittest.mock import MagicMock

        mock_httpx = MagicMock()
        mock_response = Mock()
        mock_response.text = '{"asyncapi": "3.0.0"}'
        mock_response.headers = {}  # No content-type
        mock_httpx.get.return_value = mock_response

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = SchemaLoader.load("https://example.com/schema.json")

        assert result["asyncapi"] == "3.0.0"

    def test_load_from_url_yaml_by_extension(self) -> None:
        """Test loading YAML from URL based on file extension."""
        import sys
        from unittest.mock import MagicMock

        mock_httpx = MagicMock()
        mock_response = Mock()
        mock_response.text = "asyncapi: '3.0.0'\n"
        mock_response.headers = {}  # No content-type
        mock_httpx.get.return_value = mock_response

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = SchemaLoader.load("https://example.com/schema.yml")

        assert result["asyncapi"] == "3.0.0"

    def test_load_from_url_auto_detect(self) -> None:
        """Test auto-detection when loading from URL without content-type or extension."""
        import sys
        from unittest.mock import MagicMock

        mock_httpx = MagicMock()
        mock_response = Mock()
        mock_response.text = '{"asyncapi": "3.0.0"}'
        mock_response.headers = {}
        mock_httpx.get.return_value = mock_response

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = SchemaLoader.load("https://example.com/api/schema")

        assert result["asyncapi"] == "3.0.0"

    def test_load_from_url_http_error(self) -> None:
        """Test that HTTPStatusError is converted to ValueError."""
        import sys
        from typing import Any
        from unittest.mock import MagicMock

        # Create mock exception classes that inherit from BaseException
        class MockHTTPStatusError(BaseException):
            def __init__(
                self, message: str, request: Any = None, response: Any = None
            ) -> None:
                super().__init__(message)
                self.request = request
                self.response = response

        mock_httpx = MagicMock()
        mock_httpx.HTTPStatusError = MockHTTPStatusError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_httpx.get.side_effect = MockHTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            with pytest.raises(ValueError, match="HTTP error loading schema"):
                SchemaLoader.load("https://example.com/schema.json")

    def test_load_from_url_request_error(self) -> None:
        """Test that RequestError is converted to ValueError."""
        import sys
        from unittest.mock import MagicMock

        # Create proper exception classes that inherit from BaseException
        class MockRequestError(BaseException):
            pass

        class MockHTTPStatusError(BaseException):
            pass

        mock_httpx = MagicMock()
        mock_httpx.RequestError = MockRequestError
        mock_httpx.HTTPStatusError = MockHTTPStatusError
        mock_httpx.get.side_effect = MockRequestError("Connection failed")

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            with pytest.raises(ValueError, match="Request error loading schema"):
                SchemaLoader.load("https://example.com/schema.json")

    def test_load_from_url_httpx_not_installed(self) -> None:
        """Test that helpful error is raised when httpx is not installed."""
        import sys

        # Simulate httpx not being installed
        with patch.dict(sys.modules, {"httpx": None}):
            # Clear any cached imports
            import importlib

            import chanx.client_generator.loader

            importlib.reload(chanx.client_generator.loader)

            with pytest.raises(
                ValueError, match="httpx is required to load schemas from URLs"
            ):
                chanx.client_generator.loader.SchemaLoader.load(
                    "https://example.com/schema.json"
                )
