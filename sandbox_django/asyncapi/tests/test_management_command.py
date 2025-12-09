"""Tests for generate_asyncapi_schema management command."""

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

import pytest


class TestGenerateAsyncAPISchemaCommand(TestCase):
    """Integration tests for the generate_asyncapi_schema management command."""

    def test_generate_json_to_stdout(self) -> None:
        """Test generating JSON schema to stdout."""
        out = StringIO()
        call_command("generate_asyncapi_schema", "--format=json", stdout=out)

        output = out.getvalue()
        # Verify it's valid JSON
        schema = json.loads(output)

        # Verify AsyncAPI structure
        assert "asyncapi" in schema
        assert schema["asyncapi"] == "3.0.0"
        assert "info" in schema
        assert "channels" in schema
        assert "operations" in schema

    def test_generate_yaml_to_stdout(self) -> None:
        """Test generating YAML schema to stdout."""
        pytest.importorskip("yaml")
        out = StringIO()
        call_command("generate_asyncapi_schema", "--format=yaml", stdout=out)

        output = out.getvalue()
        # Verify it's valid YAML content
        assert "asyncapi: 3.0.0" in output
        assert "info:" in output
        assert "channels:" in output

    def test_generate_json_to_file(self) -> None:
        """Test generating JSON schema to a file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            out = StringIO()
            call_command(
                "generate_asyncapi_schema",
                "--format=json",
                f"--file={tmp_path}",
                stdout=out,
            )

            # Verify file was created
            assert Path(tmp_path).exists()

            # Verify file contents
            with open(tmp_path) as f:
                schema = json.load(f)
                assert "asyncapi" in schema
                assert schema["asyncapi"] == "3.0.0"

            # Verify success message
            assert "successfully generated" in out.getvalue()

        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_generate_yaml_to_file(self) -> None:
        """Test generating YAML schema to a file."""
        pytest.importorskip("yaml")

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yaml"
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            out = StringIO()
            call_command(
                "generate_asyncapi_schema",
                "--format=yaml",
                f"--file={tmp_path}",
                stdout=out,
            )

            # Verify file was created
            assert Path(tmp_path).exists()

            # Verify file contents
            with open(tmp_path) as f:
                content = f.read()
                assert "asyncapi: 3.0.0" in content
                assert "info:" in content
                assert "channels:" in content

            # Verify success message
            assert "successfully generated" in out.getvalue()

        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_custom_base_url(self) -> None:
        """Test specifying custom base URL."""
        out = StringIO()
        call_command(
            "generate_asyncapi_schema",
            "--format=json",
            "--base-url=wss://example.com:8000",
            stdout=out,
        )

        output = out.getvalue()
        schema = json.loads(output)

        # Verify server configuration
        assert "servers" in schema
        # At least one server should use wss protocol
        server_values = list(schema["servers"].values())
        assert any(s["protocol"] == "wss" for s in server_values)

    def test_custom_metadata(self) -> None:
        """Test specifying custom title, version, and description."""
        custom_title = "Custom WebSocket API"
        custom_version = "2.5.0"
        custom_description = "This is a custom API description"

        out = StringIO()
        call_command(
            "generate_asyncapi_schema",
            "--format=json",
            f"--title={custom_title}",
            f"--api-version={custom_version}",
            f"--description={custom_description}",
            stdout=out,
        )

        output = out.getvalue()
        schema = json.loads(output)

        # Verify custom metadata
        assert schema["info"]["title"] == custom_title
        assert schema["info"]["version"] == custom_version
        assert schema["info"]["description"] == custom_description

    def test_schema_contains_chat_channels(self) -> None:
        """Test that schema includes actual chat channels from sandbox."""
        out = StringIO()
        call_command("generate_asyncapi_schema", "--format=json", stdout=out)

        output = out.getvalue()
        schema = json.loads(output)

        # Verify we have channels (sandbox has chat consumers)
        assert "channels" in schema
        channels = schema["channels"]
        assert len(channels) > 0, "Should have discovered channels from routing"

        # Verify we have operations
        assert "operations" in schema
        operations = schema["operations"]
        assert len(operations) > 0, "Should have discovered operations from handlers"

    def test_help_message(self) -> None:
        """Test that help message displays properly."""
        from django.core.management import CommandParser

        from chanx.channels.management.commands.generate_asyncapi_schema import (
            Command,
        )

        cmd = Command()
        parser = CommandParser(
            prog="generate_asyncapi_schema",
            description=cmd.help,
        )
        cmd.add_arguments(parser)

        # Get help text by formatting it
        help_text = parser.format_help()

        # Verify help text contains key information
        assert "AsyncAPI 3.0-compliant schema" in help_text
        assert "--format" in help_text
        assert "--file" in help_text
        assert "--base-url" in help_text

    def test_yaml_format_without_pyyaml_installed(self) -> None:
        """Test error when YAML format is requested but PyYAML is not installed."""
        from unittest.mock import patch

        from django.core.management.base import CommandError

        with patch(
            "chanx.channels.management.commands.generate_asyncapi_schema.yaml_available",
            False,
        ):
            with self.assertRaises(CommandError) as context:
                call_command("generate_asyncapi_schema", "--format=yaml")

            assert "PyYAML is not installed" in str(context.exception)

    def test_default_base_url_from_settings(self) -> None:
        """Test that default base URL is used when no base-url is provided."""
        from django.test import override_settings

        with override_settings(CHANX={"WEBSOCKET_BASE_URL": None}):
            out = StringIO()
            call_command("generate_asyncapi_schema", "--format=json", stdout=out)

            output = out.getvalue()
            schema = json.loads(output)

            # Should use localhost:8000 as default
            assert "servers" in schema
            server_values = list(schema["servers"].values())
            assert any("localhost" in s["host"] for s in server_values)

    def test_no_routes_generates_valid_schema(self) -> None:
        """Test that command generates valid schema even when no routes found."""
        from unittest.mock import Mock, patch

        with patch(
            "chanx.channels.management.commands.generate_asyncapi_schema.DjangoRouteDiscovery"
        ) as mock_discovery_class:
            # Mock discovery that returns no routes
            mock_discovery = Mock()
            mock_discovery.discover_routes.return_value = []
            mock_discovery_class.return_value = mock_discovery

            out = StringIO()
            call_command("generate_asyncapi_schema", "--format=json", stdout=out)

            output = out.getvalue()
            schema = json.loads(output)

            # Should still have valid AsyncAPI structure
            assert "asyncapi" in schema
            assert schema["asyncapi"] == "3.0.0"
            assert "channels" in schema

    def test_custom_discovery_class_path(self) -> None:
        """Test using a custom discovery class via path string."""
        out = StringIO()
        # Use the default DjangoRouteDiscovery class via its path
        call_command(
            "generate_asyncapi_schema",
            "--format=json",
            "--discovery-class=chanx.channels.discovery.DjangoRouteDiscovery",
            stdout=out,
        )

        output = out.getvalue()
        schema = json.loads(output)

        # Should still generate valid schema
        assert "asyncapi" in schema
        assert schema["asyncapi"] == "3.0.0"
