"""
Utility functions for FastAPI AsyncAPI documentation generation.

This module provides helper functions for extracting configuration
and server information from FastAPI applications.
"""

from typing import cast

from starlette.applications import Starlette  # noqa
from starlette.requests import Request

from .constants import ASYNCAPI_TITLE_POSTFIX
from .type_defs import DEFAULT_ASYNCAPI_CONFIG, AsyncAPIConfig

try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover
    pass


def build_default_config_from_app(
    request: Request, app: "Starlette | FastAPI"
) -> AsyncAPIConfig:
    """
    Build default AsyncAPI configuration by extracting info from FastAPI app.

    Attempts to extract server URL, title, version, and description from the
    FastAPI app instance. Falls back to static defaults if app is None or
    information cannot be extracted.

    Args:
        request: FastAPI/Starlette request instance
        app: FastAPI/Starlette app instance

    Returns:
        AsyncAPIConfig with app-specific or default values
    """
    config = dict(DEFAULT_ASYNCAPI_CONFIG)

    # Try to extract title from FastAPI app
    if title := getattr(app, "title"):
        config["title"] = title + ASYNCAPI_TITLE_POSTFIX

    # Try to extract version from FastAPI app
    if version := getattr(app, "version"):
        config["version"] = version

    # Try to extract description from FastAPI app
    if description := getattr(app, "description"):
        config["description"] = description

    # Try to extract server info from FastAPI app
    config["server_url"] = request.url.netloc

    # Determine protocol - assume ws for now, could be enhanced
    # to detect if the app is configured for TLS
    config["server_protocol"] = "wss" if request.url.scheme == "https" else "ws"

    return cast(AsyncAPIConfig, config)


def merge_configs(
    base_config: AsyncAPIConfig, user_config: AsyncAPIConfig | None
) -> AsyncAPIConfig:
    """
    Merge user configuration with base configuration.

    Args:
        base_config: Base configuration (typically from app detection)
        user_config: User-provided configuration overrides

    Returns:
        Merged configuration with user config taking precedence
    """
    if user_config is None:
        return base_config

    return {**base_config, **user_config}
