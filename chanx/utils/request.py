"""
Request utilities for translating between ASGI and Django.

This module provides utilities for working with HTTP request objects
in an ASGI context, particularly for converting WebSocket connection
scopes into Django HTTP requests. This bridge enables WebSocket
consumers to leverage Django's authentication, permissions, and
request processing infrastructure.

The primary use case is to allow WebSocket connections to be authenticated
and authorized using the same mechanisms as regular HTTP requests,
ensuring consistency across both synchronous and asynchronous parts
of a Django application.
"""

from typing import Any

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest


def request_from_scope(scope: dict[str, Any], method: str) -> HttpRequest:
    """
    Creates a Django HttpRequest from an ASGI scope dictionary.

    This utility function converts an ASGI scope (from a WebSocket or HTTP
    connection) into a Django HttpRequest object. This allows WebSocket
    consumers to use Django's authentication and permissions framework.

    Args:
        scope: The ASGI connection scope dictionary
        method: The request method

    Returns:
        A Django HttpRequest populated with data from the scope
    """
    request: HttpRequest = HttpRequest()
    request.method = method
    request.path = scope.get("path", "")
    request.COOKIES = scope.get("cookies", {})
    request.user = scope.get("user", AnonymousUser())

    for header_name, value in scope.get("headers", []):
        trans_header: str = header_name.decode("utf-8").replace("-", "_").upper()
        if not trans_header.startswith("HTTP_"):
            trans_header = "HTTP_" + trans_header
        request.META[trans_header] = value.decode("utf-8")

    return request
