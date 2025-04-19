import uuid
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar, cast

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.db.models import Manager, Model, QuerySet
from django.http import HttpRequest
from rest_framework import serializers, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import (
    BasePermission,
    OperandHolder,
    SingleOperandHolder,
)
from rest_framework.request import Request
from rest_framework.response import Response

import structlog
from asgiref.sync import sync_to_async

from chanx.utils.logging import logger
from chanx.utils.request import request_from_scope

_MT_co = TypeVar("_MT_co", bound=Model, covariant=True)


@dataclass
class AuthenticationResult:
    """
    Result of websocket authentication.

    Attributes:
        is_authenticated: Whether authentication was successful
        status_code: HTTP status code representing auth result
        status_text: Text description of status
        data: Additional data related to authentication result
        user: Authenticated user object if successful
        obj: Related model object if requested
    """

    is_authenticated: bool
    status_code: int
    status_text: str
    data: dict[str, Any] = field(default_factory=dict)
    user: AbstractBaseUser | AnonymousUser | None = None
    obj: Model | None = None


class ChanxSerializer(serializers.Serializer[Any]):
    """Base serializer for Chanx authentication."""

    detail = serializers.CharField(write_only=True, required=False)


# Type annotation to extend the DRF Request class
class ExtendedRequest(Request):
    """Extended Request class that includes an obj attribute."""

    obj: Model | None


class ChanxAuthView(GenericAPIView[Model]):
    """
    Base authentication view for Chanx websockets.

    Provides a REST-like interface for WebSocket authentication
    with Django REST Framework authentication and permissions.
    """

    serializer_class = ChanxSerializer
    detail: bool | None = None

    def get_response(self, request: ExtendedRequest) -> Response:
        """
        Get standard response with object if required.

        Args:
            request: The HTTP request object

        Returns:
            Response with OK status and object if needed
        """
        request.obj = None
        if self.detail or (self.detail is None and self.kwargs.get(self.lookup_field)):
            request.obj = self.get_object()
        return Response({"detail": "ok"})

    def get(self, request: ExtendedRequest, *args: Any, **kwargs: Any) -> Response:
        return self.get_response(request)

    def post(self, request: ExtendedRequest, *args: Any, **kwargs: Any) -> Response:
        return self.get_response(request)

    def put(self, request: ExtendedRequest, *args: Any, **kwargs: Any) -> Response:
        return self.get_response(request)

    def patch(self, request: ExtendedRequest, *args: Any, **kwargs: Any) -> Response:
        return self.get_response(request)

    def delete(self, request: ExtendedRequest, *args: Any, **kwargs: Any) -> Response:
        return self.get_response(request)


# Define a type for QuerysetLike that can be True, QuerySet, or Manager
QuerysetLike = Literal[True] | QuerySet[Any] | Manager[Any]


class ChanxWebsocketAuthenticator(Generic[_MT_co]):
    """
    Authenticator for Chanx WebSocket connections.

    Uses Django REST Framework authentication classes and permissions to authenticate
    WebSocket connections with consistent behavior to RESTful APIs.

    Attributes:
        authentication_classes: DRF authentication classes for connection verification
        permission_classes: DRF permission classes for connection authorization
        queryset: QuerySet or Manager used for retrieving objects, or True if no objects needed
        auth_method: HTTP verb to emulate for authentication
    """

    # Authentication configuration (set from consumer)
    authentication_classes: Sequence[type[BaseAuthentication]] | None = None
    permission_classes: (
        Sequence[type[BasePermission] | OperandHolder | SingleOperandHolder] | None
    ) = None
    queryset: QuerysetLike = True
    auth_method: Literal["get", "post", "put", "patch", "delete", "options"] = "get"

    def __init__(self) -> None:
        """Initialize the authenticator."""
        self._view: ChanxAuthView | None = None
        self.request: HttpRequest | None = None

    # Main public methods

    async def authenticate(self, scope: dict[str, Any]) -> AuthenticationResult:
        """
        Authenticate the WebSocket connection using DRF authentication.

        Creates an HTTP request from the WebSocket scope, applies DRF authentication,
        and returns the authentication result.

        Args:
            scope: The ASGI connection scope

        Returns:
            Authentication result with authentication status, data, user, and object
        """
        try:
            # Create a request from the WebSocket scope
            self.request = request_from_scope(scope, self.auth_method.upper())

            # Bind context for structured logging
            self._bind_structlog_request_context(self.request, scope)

            # Perform authentication
            response, request = await self._perform_dispatch(self.request, scope)

            # Store the updated request
            self.request = request

            # Extract authentication results
            status_code = response.status_code
            status_text = response.status_text
            is_authenticated = status_code == status.HTTP_200_OK

            # Parse response data
            response_data = {}
            if hasattr(response, "data"):
                if (
                    status_code < status.HTTP_500_INTERNAL_SERVER_ERROR
                ):  # Only include detailed data for non-server errors
                    response_data = (
                        response.data
                        if isinstance(response.data, dict)
                        else {"detail": response.data}
                    )

            # Success message
            if is_authenticated and not response_data:
                response_data = {"detail": "OK"}

            user = request.user
            obj = getattr(request, "obj", None)

            return AuthenticationResult(
                is_authenticated=is_authenticated,
                status_code=status_code,
                status_text=status_text,
                data=response_data,
                user=user,
                obj=obj,
            )
        except Exception as e:
            # Log the exception but don't expose details to the client
            await logger.aexception(
                f"Authentication failed with unexpected error: {str(e)}"
            )

            return AuthenticationResult(
                is_authenticated=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status_text="Internal Server Error",
                data={"detail": "Internal server error"},
                user=None,
                obj=None,
            )

    # Configuration validation methods

    def validate_configuration(self) -> None:
        """
        Validate authenticator configuration to catch common issues early.

        Warns if permissions that might need object access are used without a queryset.
        """
        # Check if we might need object retrieval
        needs_object = False
        if self.permission_classes:
            # Check if any permission class might need an object
            for perm_class in self.permission_classes:
                perm_name = getattr(perm_class, "__name__", str(perm_class))

                # Check if "Object" in name
                if "Object" in perm_name:
                    needs_object = True
                    break

                # Check if has_object_permission is overridden
                if hasattr(perm_class, "has_object_permission"):
                    # Get the method from this class directly (not from parent)
                    method = perm_class.__dict__.get("has_object_permission")
                    if (
                        method is not None
                    ):  # The method is defined in this class, not inherited
                        needs_object = True
                        break

        # Warn if we likely need an object but have no queryset
        if needs_object and self.queryset is True:
            warnings.warn(
                "The authenticator has permissions that may require object "
                "access, but no queryset is defined. This might cause errors during "
                "authentication.",
                RuntimeWarning,
                stacklevel=2,
            )

    def _validate_scope_configuration(self, scope: dict[str, Any]) -> None:
        """
        Validate that the authenticator is properly configured for the given scope.

        Args:
            scope: The ASGI connection scope

        Raises:
            ValueError: If configuration is invalid for the given scope
        """
        # Check if we have URL parameters that would trigger get_object()
        url_kwargs = scope.get("url_route", {}).get("kwargs", {})
        has_lookup_param = bool(url_kwargs)

        # If we have lookup parameters but no queryset, this will fail later
        if has_lookup_param and self.queryset is True:
            raise ValueError(
                "Object retrieval requires a queryset. Please set the 'queryset' "
                "attribute on your consumer or use an auth_class with a defined queryset."
            )

    # Helper methods

    def _get_auth_view(self) -> ChanxAuthView:
        """
        Get or create the ChanxAuthView instance.

        Returns:
            Configured ChanxAuthView instance
        """
        if self._view is None:
            self._view = ChanxAuthView()

            # Apply configuration from consumer
            if self.authentication_classes is not None:
                self._view.authentication_classes = self.authentication_classes
            if self.permission_classes is not None:
                self._view.permission_classes = self.permission_classes
            if not isinstance(
                self.queryset, bool
            ):  # Only set if it's not a boolean value
                self._view.queryset = self.queryset

        return self._view

    @sync_to_async
    def _perform_dispatch(
        self, req: HttpRequest, scope: dict[str, Any]
    ) -> tuple[Response, HttpRequest]:
        """
        Perform authentication dispatch synchronously.

        Args:
            req: The HTTP request created from the WebSocket scope
            scope: The ASGI connection scope

        Returns:
            Tuple of (response, updated request)
        """
        # Validate configuration before attempting dispatch
        self._validate_scope_configuration(scope)

        # Get the authentication view
        view = self._get_auth_view()

        # Extract URL route arguments
        url_route: dict[str, Any] = scope.get("url_route", {})
        args = url_route.get("args", [])
        kwargs = url_route.get("kwargs", {})

        # Dispatch to the view
        res = cast(Response, view.dispatch(req, *args, **kwargs))

        # Ensure response is rendered
        res.render()

        # Get updated request from renderer context
        req = (
            res.renderer_context.get("request", req)
            if hasattr(res, "renderer_context")
            else req
        )

        return res, req

    def _bind_structlog_request_context(
        self, req: HttpRequest, scope: dict[str, Any]
    ) -> None:
        """
        Bind structured logging context variables from request.

        Args:
            req: The HTTP request
            scope: The ASGI connection scope
        """
        request_id = req.headers.get("x-request-id") or str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(
            request_id=request_id, path=req.path, ip=scope.get("client", [None])[0]
        )
