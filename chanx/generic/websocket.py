import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, Literal, cast

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as BaseAsyncJsonWebsocketConsumer,
)
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import (
    BasePermission,
    OperandHolder,
    SingleOperandHolder,
)
from rest_framework.response import Response

import structlog
from asgiref.sync import sync_to_async
from pydantic import ValidationError

from chanx.generics import ChanxAuthView
from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.messages.outgoing import (
    AuthenticationMessage,
    AuthenticationPayload,
    CompleteMessage,
    ErrorMessage,
)
from chanx.settings import chanx_settings
from chanx.utils.asyncio import create_task
from chanx.utils.logging import logger
from chanx.utils.request import request_from_scope


class AsyncJsonWebsocketConsumer(BaseAsyncJsonWebsocketConsumer, ABC):  # type: ignore
    """
    Base class for asynchronous JSON WebSocket consumers with authentication and permissions.

    Provides DRF-style authentication/permissions, structured message handling with
    Pydantic validation, logging, and error handling. Subclasses must implement
    `receive_message` and set `INCOMING_MESSAGE_SCHEMA`.

    Attributes:
        permission_classes: DRF permission classes for connection authorization
        authentication_classes: DRF authentication classes for connection verification
        send_completion: Whether to send completion message after processing
        send_message_immediately: Whether to yield control after sending messages
        log_received_message: Whether to log received messages
        log_sent_message: Whether to log sent messages
        log_ignored_actions: Message actions that should not be logged
        send_authentication_message: Whether to send auth status after connection
        INCOMING_MESSAGE_SCHEMA: Pydantic model class for message validation
    """

    permission_classes: (
        Sequence[type[BasePermission] | OperandHolder | SingleOperandHolder] | None
    ) = None
    authentication_classes: Sequence[type[BaseAuthentication]] | None = None

    send_completion: bool | None = None
    send_message_immediately: bool | None = None
    log_received_message: bool | None = None
    log_sent_message: bool | None = None
    log_ignored_actions: Iterable[str] | None = None
    send_authentication_message: bool | None = None

    INCOMING_MESSAGE_SCHEMA: type[BaseIncomingMessage]

    auth_class = ChanxAuthView
    auth_method: Literal[
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
    ] = "get"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize with authentication and permission setup.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Raises:
            ValueError: If INCOMING_MESSAGE_SCHEMA is not set
        """
        super().__init__(*args, **kwargs)
        if self.send_completion is None:
            self.send_completion = chanx_settings.SEND_COMPLETION

        if self.send_message_immediately is None:
            self.send_message_immediately = chanx_settings.SEND_MESSAGE_IMMEDIATELY

        if self.log_received_message is None:
            self.log_received_message = chanx_settings.LOG_RECEIVED_MESSAGE

        if self.log_sent_message is None:
            self.log_sent_message = chanx_settings.LOG_SENT_MESSAGE

        if self.log_ignored_actions is None:
            self.log_ignored_actions = chanx_settings.LOG_IGNORED_ACTIONS

        self.ignore_actions: set[str] = (
            set(self.log_ignored_actions) if self.log_ignored_actions else set()
        )

        if self.send_authentication_message is None:
            self.send_authentication_message = (
                chanx_settings.SEND_AUTHENTICATION_MESSAGE
            )

        if not hasattr(self, "INCOMING_MESSAGE_SCHEMA"):
            raise ValueError("INCOMING_MESSAGE_SCHEMA attribute is required.")

        self._v = self.auth_class()

        if self.authentication_classes is not None:
            self._v.authentication_classes = self.authentication_classes
        if self.permission_classes is not None:
            self._v.permission_classes = self.permission_classes

        self.user: AbstractBaseUser | AnonymousUser | None = None

    # Connection lifecycle methods

    async def websocket_connect(self, message: dict[str, Any]) -> None:
        """
        Handle WebSocket connection request.

        Accepts the connection and authenticates the user.

        Args:
            message: The connection message from Channels
        """
        await self.accept()
        await self._authenticate()

    async def websocket_disconnect(self, message: dict[str, Any]) -> None:
        """
        Handle WebSocket disconnection.

        Cleans up context variables and logs the disconnection.

        Args:
            message: The disconnection message from Channels
        """
        await logger.ainfo("Disconnecting websocket")
        structlog.contextvars.clear_contextvars()
        await super().websocket_disconnect(message)

    # Message handling methods

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """
        Receive and process JSON data from WebSocket.

        Logs messages, assigns ID, and creates task for async processing.

        Args:
            content: The JSON content received from the client
            **kwargs: Additional keyword arguments
        """
        message_action = content.get(chanx_settings.MESSAGE_ACTION_KEY)

        message_id = str(uuid.uuid4())[:8]
        token = structlog.contextvars.bind_contextvars(
            message_id=message_id, received_action=message_action
        )

        if self.log_received_message and message_action not in self.ignore_actions:
            await logger.ainfo("Received websocket json")

        create_task(self._handle_receive_json_and_signal_complete(content, **kwargs))
        structlog.contextvars.reset_contextvars(**token)

    @abstractmethod
    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        """
        Process a validated received message.

        Must be implemented by subclasses to handle messages after validation.

        Args:
            message: The validated message object
            **kwargs: Additional keyword arguments
        """

    async def send_json(self, content: dict[str, Any], close: bool = False) -> None:
        """
        Send JSON data to the WebSocket client.

        Sends data and optionally logs it.

        Args:
            content: The JSON content to send
            close: Whether to close the connection after sending
        """
        await super().send_json(content, close)

        if self.send_message_immediately:
            await asyncio.sleep(0)

        message_action = content.get(chanx_settings.MESSAGE_ACTION_KEY)

        if self.log_sent_message and message_action not in self.ignore_actions:
            await logger.ainfo("Sent websocket json", sent_action=message_action)

    async def send_message(self, message: BaseMessage) -> None:
        """
        Send a Message object to the WebSocket client.

        Serializes the message and sends it as JSON.

        Args:
            message: The Message object to send
        """
        await self.send_json(message.model_dump())

    # Authentication methods

    async def _authenticate(self) -> None:
        """
        Authenticate the WebSocket connection.

        Uses DRF authentication classes and sends status if configured.
        Closes connection on authentication failure.
        """
        res, req = await self._perform_dispatch()

        self.user = req.user

        await logger.ainfo("Finished authenticating ws request")

        # We need to check status_code attribute which exists on both HttpResponse and Response
        status_code = getattr(res, "status_code", 500)
        data = getattr(res, "data", {}) if status_code != status.HTTP_200_OK else "OK"
        if self.send_authentication_message:
            await self.send_message(
                AuthenticationMessage(
                    payload=AuthenticationPayload(status_code=status_code, data=data)
                )
            )
        if status_code != status.HTTP_200_OK:
            await self.close()

    @sync_to_async
    def _perform_dispatch(self) -> tuple[Response, HttpRequest]:
        """
        Perform authentication dispatch synchronously.

        Creates request from WebSocket scope and runs it through
        the DRF authentication pipeline.

        Returns:
            Tuple of (response, request) objects
        """
        req = request_from_scope(self.scope, self.auth_method.upper())
        self._bind_structlog_request_context(req)

        logger.info("Start to authenticate ws request")
        url_route: dict[str, Any] = self.scope["url_route"]
        res = cast(
            Response, self._v.dispatch(req, *url_route["args"], **url_route["kwargs"])
        )

        # Assuming res has a render method (it does if it's a DRF Response)
        res.render()

        # For DRF Response objects, renderer_context would be available
        req = res.renderer_context.get("request")  # type: ignore

        return res, req

    def _bind_structlog_request_context(self, raw_request: HttpRequest) -> None:
        """
        Bind structured logging context variables from request.

        Extracts request ID, path and IP for consistent logging.

        Args:
            raw_request: The HTTP request object
        """
        request_id = raw_request.headers.get("x-request-id") or str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(request_id=request_id)

        structlog.contextvars.bind_contextvars(path=raw_request.path)
        structlog.contextvars.bind_contextvars(ip=self.scope.get("client", [None])[0])

    # Helper methods

    async def _handle_receive_json_and_signal_complete(
        self, content: dict[str, Any], **kwargs: Any
    ) -> None:
        """
        Handle received JSON and signal completion.

        Validates JSON against schema, processes it, handles exceptions,
        and optionally sends completion message.

        Args:
            content: The JSON content to handle
            **kwargs: Additional keyword arguments
        """
        try:
            message = self.INCOMING_MESSAGE_SCHEMA.model_validate(
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

        if self.send_completion:
            await self.send_message(CompleteMessage())
