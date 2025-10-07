"""
FastAPI integration for chanx WebSocket framework.

This module provides FastAPI-specific utilities and integrations for the chanx
WebSocket framework, allowing seamless use of chanx consumers in FastAPI applications.

Features:
- Consumer discovery and registration
- AsyncAPI documentation generation
- Interactive WebSocket playground
- FastAPI integration utilities
"""

from .views import (
    asyncapi_docs,
    asyncapi_spec_json,
    asyncapi_spec_yaml,
)

__all__ = [
    "asyncapi_spec_json",
    "asyncapi_spec_yaml",
    "asyncapi_docs",
]
