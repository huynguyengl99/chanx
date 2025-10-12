"""
Simple AsyncAPI views for FastAPI and Starlette applications.

This module provides simple view functions that can be manually added
to FastAPI or Starlette applications for AsyncAPI documentation.
"""

import json
from types import ModuleType
from typing import Any, cast

from starlette.applications import Starlette  # noqa
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

try:
    from fastapi import FastAPI  # pragma: no cover
except ImportError:
    pass

try:
    import yaml

    yaml_available: bool = True
except ImportError:
    yaml = cast(ModuleType, None)
    yaml_available = False

from chanx.asyncapi.generator import AsyncAPIGenerator

from .discovery import FastAPIRouteDiscovery
from .type_defs import AsyncAPIConfig
from .utils import build_default_config_from_app, merge_configs


def generate_asyncapi_schema(
    request: Request,
    app: "Starlette | FastAPI",
    config: AsyncAPIConfig | None = None,
) -> dict[str, Any]:
    """
    Generate AsyncAPI schema from discovered WebSocket routes in FastAPI app.

    Args:
        request: Optional FastAPI/Starlette request instance
        app: Optional FastAPI/Starlette app instance
        config: Optional AsyncAPIConfig to override detected/default values

    Returns:
        AsyncAPI schema dictionary
    """
    # Build dynamic defaults from app, then merge with user config
    app_defaults = build_default_config_from_app(request, app)
    final_config = merge_configs(app_defaults, config)

    # Create route discovery - this will walk the actual FastAPI routes
    discovery = FastAPIRouteDiscovery(app)
    routes = discovery.discover_routes()

    # Generate AsyncAPI spec using the existing generator
    generator = AsyncAPIGenerator(
        routes=routes,
        title=final_config.get("title"),
        version=final_config.get("version"),
        description=final_config.get("description"),
        server_url=final_config.get("server_url"),
        server_protocol=final_config.get("server_protocol"),
        camelize=final_config.get("camelize"),
    )

    return generator.generate()


# Simple view functions that can be used with any ASGI framework


async def asyncapi_spec_json(
    request: Request, app: "Starlette | FastAPI", config: AsyncAPIConfig | None = None
) -> JSONResponse:
    """
    Simple JSON spec endpoint that works with FastAPI, Starlette, etc.

    Usage with FastAPI:
        @app.get("/asyncapi.json")
        async def get_spec():
            return await asyncapi_spec_json(app=app)

    Usage with config:
        @app.get("/asyncapi.json")
        async def get_spec():
            return await asyncapi_spec_json(app=app, config={"title": "My API"})

    Usage with Starlette:
        Route("/asyncapi.json", asyncapi_spec_json)
    """

    try:
        schema = generate_asyncapi_schema(request=request, app=app, config=config)
        return JSONResponse(schema)
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to generate schema: {str(e)}"}, status_code=500
        )


async def asyncapi_spec_yaml(
    request: Request, app: "Starlette | FastAPI", config: AsyncAPIConfig | None = None
) -> Response:
    """
    Simple YAML spec endpoint that works with FastAPI, Starlette, etc.
    """

    if not yaml_available:
        from starlette.responses import JSONResponse

        return JSONResponse(
            {
                "error": (
                    "YAML format not available. Please install PyYAML: pip install PyYAML"
                )
            },
            status_code=400,
        )

    try:
        schema = generate_asyncapi_schema(request=request, app=app, config=config)
        yaml_content = yaml.dump(schema, default_flow_style=False, sort_keys=False)
        return Response(content=yaml_content, media_type="application/x-yaml")
    except Exception as e:
        from starlette.responses import JSONResponse

        return JSONResponse(
            {"error": f"Failed to generate schema: {str(e)}"}, status_code=500
        )


async def asyncapi_docs(
    request: Request,
    app: "Starlette | FastAPI",
    config: AsyncAPIConfig | None = None,
) -> HTMLResponse:
    """
    Simple AsyncAPI docs endpoint that works with FastAPI, Starlette, etc.
    Follows the same template structure as Django's channels extension.
    """

    try:
        # Get the schema directly for injection
        schema = generate_asyncapi_schema(request=request, app=app, config=config)
        schema_json = json.dumps(schema)

        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>{schema['info']['title']}</title>
                <link rel="stylesheet" href="https://unpkg.com/@asyncapi/react-component@latest/styles/default.min.css">
            </head>
            <body>
                <div id="asyncapi"></div>

                <script src="https://unpkg.com/@asyncapi/react-component@latest/browser/standalone/index.js"></script>
                <script>
                    AsyncApiStandalone.render({{
                        schema: {schema_json},
                        config: {{
                            show: {{
                                sidebar: true,
                            }}
                        }},
                    }}, document.getElementById('asyncapi'));
                </script>
            </body>
        </html>
        """.strip()
        return HTMLResponse(html_content)

    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>AsyncAPI Schema</title>
                <link rel="stylesheet" href="https://unpkg.com/@asyncapi/react-component@latest/styles/default.min.css">
            </head>
            <body>
                <div style="padding: 2rem; background: #fee; border: 1px solid #fcc; margin: 2rem; border-radius: 8px; color: #c33;">
                    <h3>Error</h3>
                    <p>{str(e)}</p>
                </div>
            </body>
        </html>
        """.strip()
        return HTMLResponse(error_html, status_code=500)
