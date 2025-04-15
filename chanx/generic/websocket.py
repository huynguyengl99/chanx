import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, cast

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as BaseAsyncJsonWebsocketConsumer,
)
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponseBase
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import (
    BasePermission,
    OperandHolder,
    SingleOperandHolder,
)
from rest_framework.settings import api_settings
from rest_framework.views import APIView

import structlog
from asgiref.sync import sync_to_async
from pydantic import ValidationError

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.messages.outgoing import (
    AuthenticationMessage,
    AuthenticationPayload,
    CompleteMessage,
    ErrorMessage,
)
from chanx.settings import chanx_settings
from chanx.utils import create_task, get_request_header, logger, request_from_scope


class AsyncJsonWebsocketConsumer(BaseAsyncJsonWebsocketConsumer, ABC):  # type: ignore
    """
    Base class for asynchronous JSON WebSocket consumers with authentication and permission handling.

    This class extends Django Channels' AsyncJsonWebsocketConsumer to provide authentication,
    permission checking, structured message handling, and logging.
    """

    permission_classes: Sequence[
        type[BasePermission] | OperandHolder | SingleOperandHolder
    ] = cast(Sequence[type[BasePermission]], api_settings.DEFAULT_PERMISSION_CLASSES)
    authentication_classes: Sequence[type[BaseAuthentication]] = cast(
        Sequence[type[BaseAuthentication]],
        chanx_settings.DEFAULT_AUTHENTICATION_CLASSES
        or api_settings.DEFAULT_AUTHENTICATION_CLASSES,
    )

    send_completion: bool = chanx_settings.SEND_COMPLETION
    send_message_immediately: bool = chanx_settings.SEND_MESSAGE_IMMEDIATELY
    silent_actions: set[str] = set()
    log_received_message: bool = chanx_settings.LOG_RECEIVED_MESSAGE
    log_sent_message: bool = chanx_settings.LOG_SENT_MESSAGE
    log_ignored_actions: Iterable[str] = chanx_settings.LOG_IGNORED_ACTIONS
    INCOMING_MESSAGE_SCHEMA: type[BaseIncomingMessage] = (
        chanx_settings.INCOMING_MESSAGE_SCHEMA
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the WebSocket consumer with authentication and permission setup.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

        self._v = APIView()
        self._v.authentication_classes = self.authentication_classes
        self._v.permission_classes = self.permission_classes
        self.user: AbstractBaseUser | AnonymousUser | None = None

    # Connection lifecycle methods

    async def websocket_connect(self, message: dict[str, Any]) -> None:
        """
        Handle WebSocket connection request.

        This method is called when a client attempts to establish a WebSocket connection.
        It accepts the connection and authenticates the user.

        Args:
            message: The connection message.
        """
        await self.accept()
        await self._authenticate()

    async def websocket_disconnect(self, message: dict[str, Any]) -> None:
        """
        Handle WebSocket disconnection.

        This method is called when a client disconnects from the WebSocket.
        It cleans up context variables and logs the disconnection.

        Args:
            message: The disconnection message.
        """
        await logger.ainfo("Disconnecting websocket")
        structlog.contextvars.clear_contextvars()
        await super().websocket_disconnect(message)

    # Message handling methods

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """
        Receive and process JSON data from the WebSocket.

        This method is called when a client sends a JSON message. It logs the received
        message and creates a task to handle it asynchronously.

        Args:
            content: The JSON content received from the client.
            **kwargs: Additional keyword arguments.
        """
        message_action = content.get(chanx_settings.MESSAGE_ACTION_KEY)

        message_id = str(uuid.uuid4())[:8]
        token = structlog.contextvars.bind_contextvars(
            message_id=message_id, received_action=message_action
        )

        if self.log_received_message:
            await logger.ainfo("Received websocket json")

        create_task(self._handle_receive_json_and_signal_complete(content, **kwargs))
        structlog.contextvars.reset_contextvars(**token)

    @abstractmethod
    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        """
        Process a received message.

        This abstract method must be implemented by subclasses to handle
        received messages after they've been deserialized.

        Args:
            message: The deserialized Message object.
            **kwargs: Additional keyword arguments.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError

    async def send_json(self, content: dict[str, Any], close: bool = False) -> None:
        """
        Send JSON data to the WebSocket client.

        This method sends a JSON message to the client and optionally logs it.

        Args:
            content: The JSON content to send.
            close: Whether to close the connection after sending.
        """
        await super().send_json(content, close)

        if self.send_message_immediately:
            await asyncio.sleep(0)

        message_action = content.get(chanx_settings.MESSAGE_ACTION_KEY)

        if self.log_sent_message:
            await logger.ainfo("Sent websocket json", sent_action=message_action)

    async def send_message(self, message: BaseMessage) -> None:
        """
        Send a Message object to the WebSocket client.

        This method serializes a Message object and sends it to the client.

        Args:
            message: The Message object to send.
        """
        await self.send_json(message.model_dump())

    # Authentication methods

    async def _authenticate(self) -> None:
        """
        Authenticate the WebSocket connection.

        This method authenticates the WebSocket connection using the configured
        authentication classes and sets the user attribute.
        """
        res, req = await self._perform_dispatch()

        self.user = req.user if hasattr(req, "user") else None

        await logger.ainfo("Finished authenticating ws request")

        # We need to check status_code attribute which exists on both HttpResponse and Response
        status_code = getattr(res, "status_code", 500)
        data = getattr(res, "data", {})
        if chanx_settings.SEND_AUTHENTICATION_MESSAGE:
            await self.send_message(
                AuthenticationMessage(
                    payload=AuthenticationPayload(status_code=status_code, data=data)
                )
            )
        if status_code != status.HTTP_200_OK:
            await self.close()

    @sync_to_async
    def _perform_dispatch(self) -> tuple[HttpResponseBase, HttpRequest]:
        """
        Perform authentication dispatch synchronously.

        This method creates a request from the WebSocket scope, binds logging context,
        and dispatches the request through the authentication pipeline.

        Returns:
            A tuple containing the response and request objects.
        """
        raw_request = request_from_scope(self.scope)
        self._bind_structlog_request_context(raw_request)

        logger.info("Start to authenticate ws request")

        res = self._v.dispatch(raw_request)

        # Assuming res has a render method (it does if it's a DRF Response)
        if hasattr(res, "render"):
            res.render()

        # For DRF Response objects, renderer_context would be available
        if hasattr(res, "renderer_context"):
            req = res.renderer_context.get("request")
        else:
            # Fallback to the original request if renderer_context is not available
            req = raw_request

        return res, req

    def _bind_structlog_request_context(self, raw_request: HttpRequest) -> None:
        """
        Bind structured logging context variables from request.

        This method extracts and binds request metadata to the structured logging context.

        Args:
            raw_request: The HTTP request object.
        """
        request_id = get_request_header(
            raw_request, "x-request-id", "HTTP_X_REQUEST_ID"
        ) or str(uuid.uuid4())
        correlation_id = get_request_header(
            raw_request, "x-correlation-id", "HTTP_X_CORRELATION_ID"
        )
        structlog.contextvars.bind_contextvars(request_id=request_id)

        if correlation_id:
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        structlog.contextvars.bind_contextvars(path=raw_request.path)
        structlog.contextvars.bind_contextvars(ip=self.scope.get("client", [None])[0])

    # Helper methods

    async def _handle_receive_json_and_signal_complete(
        self, content: dict[str, Any], **kwargs: Any
    ) -> None:
        """
        Handle received JSON content and signal completion.

        This method deserializes the JSON content into a Message object, calls the
        receive_message method, and optionally sends a completion signal.

        Args:
            content: The JSON content to handle.
            **kwargs: Additional keyword arguments.
        """
        try:
            # Using the discriminator field pattern
            try:
                # For Pydantic v2
                message = self.INCOMING_MESSAGE_SCHEMA.model_validate(
                    {"message": content}
                ).message
            except AttributeError:
                # For Pydantic v1
                message = self.INCOMING_MESSAGE_SCHEMA.parse_obj(
                    {"message": content}
                ).message

            await self.receive_message(message, **kwargs)
        except ValidationError as e:
            await self.send_message(
                ErrorMessage(
                    payload=e.errors(
                        include_url=False, include_context=False, include_input=False
                    )
                )
            )
        except Exception as e:
            await logger.aexception(f"Failed to process message: {str(e)}")
            await self.send_message(
                ErrorMessage(payload={"detail": "Failed to process message"})
            )
            return

        if self.send_completion:
            await self.send_message(CompleteMessage())
