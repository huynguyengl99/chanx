"""
Django management command to generate AsyncAPI schema file.

This command generates an AsyncAPI 3.0-compliant schema for your WebSocket API
without requiring an HTTP request-response flow.
"""

import json
from textwrap import dedent
from types import ModuleType
from typing import Any, cast

from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory
from django.utils.module_loading import import_string

from chanx.asyncapi.generator import AsyncAPIGenerator
from chanx.channels.discovery import DjangoRouteDiscovery
from chanx.channels.settings import chanx_settings

try:
    import yaml

    yaml_available = True
except ImportError:  # pragma: no cover
    yaml = cast(ModuleType, None)
    yaml_available = False


class SchemaGenerationError(CommandError):
    """Exception raised when schema generation fails."""

    pass


class Command(BaseCommand):
    """Management command to generate AsyncAPI schema."""

    help = dedent(
        """
        Generate an AsyncAPI 3.0-compliant schema for your WebSocket API.

        This command introspects your Django Channels routing configuration and
        generates a complete AsyncAPI specification file that can be used for
        documentation, code generation, and API testing.

        The command supports both JSON and YAML output formats and can write
        to a file or stdout.

        Example usage:
            # Generate YAML schema and write to file
            python manage.py generate_asyncapi_schema --format yaml --file schema.yaml

            # Generate JSON schema to stdout
            python manage.py generate_asyncapi_schema --format json

            # Use custom settings and base URL
            python manage.py generate_asyncapi_schema --base-url ws://example.com --format yaml
        """
    )

    def add_arguments(self, parser: Any) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--format",
            dest="format",
            choices=["json", "yaml"],
            default="yaml",
            type=str,
            help="Output format (json or yaml)",
        )
        parser.add_argument(
            "--file",
            dest="file",
            default=None,
            type=str,
            help="Output file path (if not specified, outputs to stdout)",
        )
        parser.add_argument(
            "--base-url",
            dest="base_url",
            default=None,
            type=str,
            help="WebSocket base URL (e.g., ws://localhost:8000)",
        )
        parser.add_argument(
            "--title",
            dest="title",
            default=None,
            type=str,
            help="API title for AsyncAPI documentation",
        )
        parser.add_argument(
            "--api-version",
            dest="api_version",
            default=None,
            type=str,
            help="API version for AsyncAPI documentation",
        )
        parser.add_argument(
            "--description",
            dest="description",
            default=None,
            type=str,
            help="API description for AsyncAPI documentation",
        )
        parser.add_argument(
            "--discovery-class",
            dest="discovery_class",
            default=None,
            type=str,
            help="Custom route discovery class path",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        # Check if YAML is required but not available
        if options["format"] == "yaml" and not yaml_available:
            raise SchemaGenerationError(
                "YAML format requested but PyYAML is not installed. "
                "Please install it: pip install PyYAML"
            )

        try:
            # Generate the schema
            schema = self._generate_schema(options)

            # Render the schema in the requested format
            output = self._render_schema(schema, options["format"])

            # Write to file or stdout
            if options["file"]:
                with open(options["file"], "wb") as f:
                    f.write(output)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"AsyncAPI schema successfully generated: {options['file']}"
                    )
                )
            else:
                self.stdout.write(output.decode())

        except Exception as e:
            raise SchemaGenerationError(f"Failed to generate schema: {str(e)}") from e

    def _generate_schema(self, options: dict[str, Any]) -> dict[str, Any]:
        """
        Generate AsyncAPI schema.

        Args:
            options: Command options

        Returns:
            AsyncAPI schema dictionary
        """
        # Get or create route discovery instance
        if options.get("discovery_class"):
            discovery_class = import_string(options["discovery_class"])
            discovery = discovery_class()
        else:
            discovery = DjangoRouteDiscovery()

        # Determine base URL
        base_url = options.get("base_url") or self._get_default_base_url()

        # Discover routes
        routes = discovery.discover_routes(base_url)

        if not routes:
            self.stderr.write(
                self.style.WARNING(
                    "No WebSocket routes found. Make sure your ASGI application "
                    "is properly configured."
                )
            )

        # Create a fake request for settings that need it
        request_factory = RequestFactory()
        request_factory.get("/")

        # Parse base URL for server configuration
        server_url, server_protocol = self._parse_base_url(base_url)

        # Use custom settings or fall back to defaults
        title = options.get("title") or chanx_settings.ASYNCAPI_TITLE
        version = options.get("api_version") or chanx_settings.ASYNCAPI_VERSION
        description = options.get("description") or chanx_settings.ASYNCAPI_DESCRIPTION

        # Generate AsyncAPI schema using the generator
        generator = AsyncAPIGenerator(
            routes,
            title=title,
            version=version,
            description=description,
            server_url=server_url,
            server_protocol=server_protocol,
            camelize=chanx_settings.CAMELIZE,
        )

        return generator.generate()

    def _get_default_base_url(self) -> str:
        """
        Get default base URL from settings or use localhost.

        Returns:
            Default WebSocket base URL
        """
        if chanx_settings.WEBSOCKET_BASE_URL:
            return chanx_settings.WEBSOCKET_BASE_URL
        return "ws://localhost:8000"

    def _parse_base_url(self, base_url: str) -> tuple[str, str]:
        """
        Parse base URL into server URL and protocol.

        Args:
            base_url: Full WebSocket URL (e.g., ws://localhost:8000)

        Returns:
            Tuple of (server_url, protocol)
        """
        # Extract protocol (ws or wss)
        if base_url.startswith("wss://"):
            protocol = "wss"
            server_url = base_url[6:]  # Remove 'wss://'
        elif base_url.startswith("ws://"):
            protocol = "ws"
            server_url = base_url[5:]  # Remove 'ws://'
        else:
            # Default to ws if no protocol specified
            protocol = "ws"
            server_url = base_url

        return server_url, protocol

    def _render_schema(self, schema: dict[str, Any], format_type: str) -> bytes:
        """
        Render schema in the requested format.

        Args:
            schema: AsyncAPI schema dictionary
            format_type: Output format ('json' or 'yaml')

        Returns:
            Rendered schema as bytes
        """
        if format_type == "yaml":
            yaml_content = yaml.dump(
                schema,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                allow_unicode=True,
            )
            return yaml_content.encode("utf-8")
        else:
            json_content = json.dumps(schema, indent=2, ensure_ascii=False)
            return json_content.encode("utf-8")
