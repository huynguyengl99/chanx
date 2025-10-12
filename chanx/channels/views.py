"""
Views for Chanx Channels extension.

This module provides Django views for generating and serving AsyncAPI documentation
from Chanx WebSocket consumers using the new @channel decorator system.
"""

import json
from types import ModuleType
from typing import Any, cast

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from chanx.asyncapi.generator import AsyncAPIGenerator
from chanx.channels.discovery import get_websocket_routes
from chanx.channels.settings import chanx_settings

try:
    import yaml

    yaml_available = True
except ImportError:  # pragma: no cover
    yaml = cast(ModuleType, None)
    yaml_available = False


def generate_asyncapi_schema(request: HttpRequest) -> dict[str, Any]:
    """
    Generate AsyncAPI 3.0 schema using the new generator system.

    Args:
        request: The HTTP request object to determine WebSocket base URL

    Returns:
        AsyncAPI schema dictionary
    """
    # Pass the request to get_websocket_routes so it can determine the proper base URL
    routes = get_websocket_routes(request)

    # Use the new AsyncAPI generator with configurable settings
    generator = AsyncAPIGenerator(
        routes,
        title=chanx_settings.ASYNCAPI_TITLE,
        version=chanx_settings.ASYNCAPI_VERSION,
        description=chanx_settings.ASYNCAPI_DESCRIPTION,
        server_url=chanx_settings.ASYNCAPI_SERVER_URL or request.get_host(),
        server_protocol=chanx_settings.ASYNCAPI_SERVER_PROTOCOL
        or ("wss" if request.is_secure() else "ws"),
        camelize=chanx_settings.CAMELIZE,
    )

    return generator.generate()


class AsyncAPISchemaView(View):
    """
    Django view to generate AsyncAPI schema from WebSocket routing.

    This view introspects the ASGI application routing to find all WebSocket consumers,
    extracts their handler information, and generates an AsyncAPI 3.0 schema.
    Supports both JSON and YAML output formats.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Generate and return AsyncAPI schema in requested format (JSON or YAML)."""
        # Get the requested format from query parameter
        format_param = request.GET.get("format", "json").lower()

        # Validate format
        if format_param not in ["json", "yaml"]:
            return JsonResponse(
                {"error": "Invalid format. Supported formats: json, yaml"},
                status=400,
            )

        # Check if YAML is requested but not available
        if format_param == "yaml" and not yaml_available:
            return JsonResponse(
                {
                    "error": (
                        "YAML format not available. Please install PyYAML: "
                        "pip install PyYAML"
                    )
                },
                status=400,
            )

        try:
            # Generate schema
            schema = generate_asyncapi_schema(request)

            # Return in requested format
            if format_param == "yaml":
                return self._return_yaml_response(schema)
            else:
                return JsonResponse(schema, json_dumps_params={"indent": 2})

        except Exception as e:
            return JsonResponse(
                {"error": f"Failed to generate schema: {str(e)}"},
                status=500,
            )

    def _return_yaml_response(self, data: dict[str, Any]) -> HttpResponse:
        """Return data as YAML response with proper content type."""
        yaml_content = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            allow_unicode=True,
        )

        return HttpResponse(
            yaml_content,
            status=200,
            content_type="application/yaml; charset=utf-8",
        )


class AsyncAPIDocsView(View):
    """
    Django view to render AsyncAPI documentation with interactive UI.

    This view renders the AsyncAPI schema in a user-friendly HTML interface
    using AsyncAPI's official HTML template or a custom template.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render AsyncAPI documentation page."""

        try:
            # Generate the schema directly
            schema = generate_asyncapi_schema(request)

            # Get the schema as JSON string for the template (for direct injection)
            schema_json = json.dumps(schema)

            context = {
                "schema_json": schema_json,
            }

            # Use Django's render since we're returning HTML
            return render(request, "channels/asyncapi_docs.html", context)

        except Exception as e:
            # Render error page
            context = {
                "error": f"Failed to generate documentation: {str(e)}",
                "title": "AsyncAPI Documentation - Error",
            }
            return render(request, "channels/asyncapi_docs.html", context, status=500)
