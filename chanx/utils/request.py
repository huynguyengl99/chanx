from typing import Any

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest


def request_from_scope(scope: dict[str, Any]) -> HttpRequest:
    request: HttpRequest = HttpRequest()
    request.method = "OPTIONS"
    request.path = scope.get("path", "")
    request.COOKIES = scope.get("cookies", {})
    request.user = scope.get("user", AnonymousUser())

    for header_name, value in scope.get("headers", []):
        trans_header: str = header_name.decode("utf-8").replace("-", "_").upper()
        if not trans_header.startswith("HTTP_"):
            trans_header = "HTTP_" + trans_header
        request.META[trans_header] = value.decode("utf-8")

    return request
