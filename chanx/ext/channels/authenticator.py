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
- ChanxAuthView: DRF-compatible view for processing authentication
- ChanxWebsocketAuthenticator: Main authenticator that processes WebSocket connections
"""

import uuid
from collections.abc import Sequence
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

from chanx.core.authenticator import BaseAuthenticator
from chanx.ext.channels.utils import request_from_scope
from chanx.messages.outgoing import AuthenticationMessage, AuthenticationPayload
from chanx.type_defs import SendMessageFn
from chanx.utils.logging import logger


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


class DjangoAuthenticator(BaseAuthenticator):
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
    queryset: QuerySet[Any] | Manager[Any] | None = None
    auth_method: Literal["get", "post", "put", "patch", "delete", "options"] = "get"
    lookup_field: str = "pk"
    lookup_url_kwarg: str | None = None

    user: AbstractBaseUser | AnonymousUser | None = None
    obj: Model | None = None

    def __init__(self, send_message: SendMessageFn):
        """Initialize the authenticator."""

        super().__init__(send_message)
        self._view: ChanxAuthView
        self.request: HttpRequest | None = None

    # Main public methods

    async def authenticate(self, scope: dict[str, Any]) -> bool:
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

            self.user = request.user
            try:
                self.get_queryset()
                if status_code == status.HTTP_200_OK:
                    self.obj = await sync_to_async(self._view.get_object)()
            except AssertionError:
                pass

            await self.send_message(
                AuthenticationMessage(
                    payload=AuthenticationPayload(
                        status_code=status_code,
                        status_text=status_text,
                        data=response_data,
                    )
                )
            )

            return is_authenticated
        except Exception as e:
            # Log the exception but don't expose details to the client
            await logger.aexception(
                f"Authentication failed with unexpected error: {str(e)}"
            )

            return False

    def get_queryset(self) -> QuerySet[Any]:
        """
        Get the queryset used for object retrieval during authentication.

        This method returns the queryset that will be used by the authentication
        view to retrieve objects for permission checks. Defaults to using `self.queryset`.

        Override this method in your authenticator subclass if you need to provide
        different querysets based on the authenticated user or request context.

        Returns:
            A QuerySet for object retrieval

        Raises:
            AssertionError: If neither `queryset` attribute is set nor this method is overridden
        """
        assert self.queryset is not None, (
            f"'{self.__class__.__name__}' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
        )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
        return cast(QuerySet[Any], queryset)

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
        if self.queryset is not None:
            self._view.queryset = self.queryset

        self._view.get_queryset = self.get_queryset  # type: ignore[method-assign]

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
