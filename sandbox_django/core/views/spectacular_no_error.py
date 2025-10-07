import contextlib
from collections.abc import Iterator
from typing import Any, cast

from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,  # pyright: ignore[reportUnknownVariableType]
)
from drf_spectacular.views import SpectacularAPIView


@contextlib.contextmanager
def alter_error_schema() -> Iterator[None]:
    from drf_standardized_errors.openapi import AutoSchema

    # Store the original method
    old_schema_should_add_error_response = (  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        AutoSchema._should_add_error_response  # pyright: ignore[reportPrivateUsage]
    )  # noqa

    # Define the replacement method with proper typing
    def new_schema_should_add_error_response(
        self: Any, responses: dict[str, Any], status_code: str
    ) -> bool:
        return False

    try:
        # Use monkey patching to replace the method
        # We need to use setattr to avoid the mypy error about assigning to a method
        AutoSchema._should_add_error_response = new_schema_should_add_error_response  # type: ignore
        yield
    finally:
        # Restore the original method
        AutoSchema._should_add_error_response = old_schema_should_add_error_response  # type: ignore


class SpectacularNoErrorAPIView(SpectacularAPIView):
    """
    Custom API view that generates schema documentation without error responses.

    This view extends SpectacularAPIView to produce a schema that excludes error definitions,
    which is useful for API-based code generation. By omitting repetitive error schemas,
    the generated documentation remains concise and more manageable in size.
    """

    @extend_schema(exclude=True)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        with alter_error_schema():
            return cast(Response, super().get(request, *args, **kwargs))  # type: ignore[no-untyped-call]
