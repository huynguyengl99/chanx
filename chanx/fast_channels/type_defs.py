"""
Type definitions for FastAPI AsyncAPI documentation.

This module provides TypedDict definitions for configuration and other
typed interfaces used in FastAPI AsyncAPI generation.
"""

from typing import NotRequired, TypedDict

from chanx.asyncapi.constants import (
    DEFAULT_ASYNCAPI_DESCRIPTION,
    DEFAULT_ASYNCAPI_TITLE,
    DEFAULT_ASYNCAPI_VERSION,
    DEFAULT_SERVER_PROTOCOL,
    DEFAULT_SERVER_URL,
)


class AsyncAPIConfig(TypedDict, total=False):
    """
    Configuration options for AsyncAPI documentation generation.

    All fields are optional and will override the default parameters
    when provided to AsyncAPI generation functions.

    Attributes:
        title: API title for the AsyncAPI specification
        version: API version string
        description: API description text
        server_url: Server URL for WebSocket connections
        server_protocol: Protocol (ws or wss)
        camelize: Whether to convert all keys to camelCase (default: False)
        docs_js_url: Docs page script URL (default: pinned CDN)
        docs_css_url: Docs page stylesheet URL (default: pinned CDN)
        docs_js_integrity: SRI hash for the script (default: pinned hash for the CDN URL)
        docs_css_integrity: SRI hash for the stylesheet (default: pinned hash for the CDN URL)
    """

    title: NotRequired[str]
    version: NotRequired[str]
    description: NotRequired[str]
    server_url: NotRequired[str]
    server_protocol: NotRequired[str]
    camelize: NotRequired[bool]
    docs_js_url: NotRequired[str]
    docs_css_url: NotRequired[str]
    docs_js_integrity: NotRequired[str]
    docs_css_integrity: NotRequired[str]


# Default configuration using constants
DEFAULT_ASYNCAPI_CONFIG: AsyncAPIConfig = {
    "title": DEFAULT_ASYNCAPI_TITLE,
    "version": DEFAULT_ASYNCAPI_VERSION,
    "description": DEFAULT_ASYNCAPI_DESCRIPTION,
    "server_url": DEFAULT_SERVER_URL,
    "server_protocol": DEFAULT_SERVER_PROTOCOL,
    "camelize": False,
}
