"""
WebSocket authentication system for Chanx using Django REST Framework.

This module provides a bridge between WebSocket connections and Django REST
Framework's authentication and permission systems. It enables WebSocket
connections to be authenticated and authorized using the same mechanisms
as RESTful APIs, ensuring consistency across your application.

The authenticator translates ASGI WebSocket connection scopes into Django HTTP
requests that can be processed by DRF authentication classes and permission
checks. It supports object-level permissions and handles validation of
configuration to prevent common errors.

Key components:
- AuthenticationResult: Dataclass for authentication outcomes
- ChanxAuthView: DRF-compatible view for processing authentication
- ChanxWebsocketAuthenticator: Main authenticator that processes WebSocket connections
"""

import re
import uuid
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast

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
    data: dict[str, Any] = field(default_factory=dict[str, Any])
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

    def get_response(self, request: Request) -> Response:
        """
        Get standard response with object if required.

        Args:
            request: The HTTP request object

        Returns:
            Response with OK detail
        """
        if isinstance(self.queryset, QuerySet):
            _ = self.get_object()
        return Response({"detail": "ok"})

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Stub get method"""
        return self.get_response(request)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Stub post method"""

        return self.get_response(request)

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Stub put method"""

        return self.get_response(request)

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Stub patch method"""

        return self.get_response(request)

    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Stub delete method"""

        return self.get_response(request)


# Define a type for QuerysetLike that can be True, QuerySet, or Manager
QuerysetLike = Literal[True] | QuerySet[Any] | Manager[Any]


class ChanxWebsocketAuthenticator:
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
    lookup_field: str = "pk"
    lookup_url_kwarg: str | None = None

    def __init__(self) -> None:
        """Initialize the authenticator."""
        self._view: ChanxAuthView
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
            response_data = response.data

            # Success message
            if is_authenticated:
                response_data = {"detail": "OK"}

            user = request.user
            obj: Model | None = None
            if self.queryset is not True and status_code == status.HTTP_200_OK:
                obj = await sync_to_async(self._view.get_object)()

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
        regex = r"(^|\.)BasePermission."
        if self.permission_classes:
            # Check if any permission class might need an object
            for perm_class in self.permission_classes:
                if hasattr(perm_class, "has_object_permission") and issubclass(perm_class, BasePermission):  # type: ignore
                    meth = perm_class.has_object_permission
                    qname = meth.__qualname__

                    if not re.match(regex, qname):
                        needs_object = True
                        break

        # Warn if we likely need an object but have no queryset
        if needs_object and self.queryset is True:
            warnings.warn(
                "The authenticator has permissions that may require object "
                + "access, but no queryset is defined. This might cause errors during "
                + "authentication.",
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
                + "attribute on your consumer or use an auth_class with a defined queryset."
            )

    # Helper methods

    def _setup_auth_view(self) -> None:
        """
        Get or create the ChanxAuthView instance.

        Returns:
            Configured ChanxAuthView instance
        """
        self._view = ChanxAuthView()

        # Apply configuration from consumer
        if self.authentication_classes is not None:
            self._view.authentication_classes = self.authentication_classes
        if self.permission_classes is not None:
            self._view.permission_classes = self.permission_classes
        if not isinstance(self.queryset, bool):  # Only set if it's not a boolean value
            self._view.queryset = self.queryset

        self._view.lookup_field = self.lookup_field
        self._view.lookup_url_kwarg = self.lookup_url_kwarg

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
        self._setup_auth_view()

        # Extract URL route arguments
        url_route: dict[str, Any] = scope.get("url_route", {})
        args = url_route.get("args", [])
        kwargs = url_route.get("kwargs", {})

        # Dispatch to the view
        res = cast(Response, self._view.dispatch(req, *args, **kwargs))

        # Ensure response is rendered
        res.render()

        # Get updated request from renderer context
        req = self._view.request

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

        _ = structlog.contextvars.bind_contextvars(
            request_id=request_id, path=req.path, ip=scope.get("client", [None])[0]
        )
