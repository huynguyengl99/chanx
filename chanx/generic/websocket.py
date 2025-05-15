"""
Authenticated WebSocket consumer system for Chanx.

This module provides the core WebSocket consumer implementation for Chanx,
offering a robust framework for building real-time applications with Django
Channels and Django REST Framework. The AsyncJsonWebsocketConsumer serves as the
foundation for WebSocket connections with integrated authentication, permissions,
structured message handling, and group messaging capabilities.

Key features:
- DRF-style authentication and permission checking
- Structured message handling with Pydantic validation
- Automatic group management for pub/sub messaging
- Comprehensive error handling and reporting
- Configurable logging and message completion signals
- Support for object-level permissions and retrieval

Developers should subclass AsyncJsonWebsocketConsumer and implement the
receive_message method to handle incoming messages. The consumer automatically
handles connection lifecycle, authentication, message validation, and group
messaging.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from types import ModuleType
from typing import (
    Any,
    Generic,
    Literal,
    cast,
)

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as BaseAsyncJsonWebsocketConsumer,
)
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Model
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import (
    BasePermission,
    OperandHolder,
    SingleOperandHolder,
)

import structlog
from asgiref.typing import WebSocketConnectEvent, WebSocketDisconnectEvent
from pydantic import ValidationError
from typing_extensions import TypeVar

from chanx.constants import MISSING_PYHUMPS_ERROR
from chanx.generic.authenticator import ChanxWebsocketAuthenticator, QuerysetLike
from chanx.messages.base import (
    BaseIncomingMessage,
    BaseMessage,
    BaseOutgoingGroupMessage,
)
from chanx.messages.outgoing import (
    AuthenticationMessage,
    AuthenticationPayload,
    CompleteMessage,
    ErrorMessage,
    GroupCompleteMessage,
)
from chanx.settings import chanx_settings
from chanx.types import GroupMemberEvent
from chanx.utils.asyncio import create_task
from chanx.utils.logging import logger

try:
    import humps
except ImportError:  # pragma: no cover
    humps = cast(ModuleType, None)  # pragma: no cover


_M = TypeVar("_M", bound=Model, default=Model)


class AsyncJsonWebsocketConsumer(Generic[_M], BaseAsyncJsonWebsocketConsumer, ABC):
    """
    Base class for asynchronous JSON WebSocket consumers with authentication and permissions.

    Provides DRF-style authentication/permissions, structured message handling with
    Pydantic validation, logging, and error handling. Subclasses must implement
    `receive_message` and set `INCOMING_MESSAGE_SCHEMA`.

    For group messaging functionality, subclasses should also define
    `OUTGOING_GROUP_MESSAGE_SCHEMA` to enable proper validation and handling
    of group message broadcasts.

    Attributes:
        authentication_classes: DRF authentication classes for connection verification
        permission_classes: DRF permission classes for connection authorization
        queryset: QuerySet or Manager used for retrieving objects
        auth_method: HTTP verb to emulate for authentication
        authenticator_class: Class to use for performing websocket authentication, defaults to ChanxWebsocketAuthenticator
        send_completion: Whether to send completion message after processing
        send_message_immediately: Whether to yield control after sending messages
        log_received_message: Whether to log received messages
        log_sent_message: Whether to log sent messages
        log_ignored_actions: Message actions that should not be logged
        send_authentication_message: Whether to send auth status after connection
        INCOMING_MESSAGE_SCHEMA: Pydantic model class for validating incoming messages
        OUTGOING_GROUP_MESSAGE_SCHEMA: Pydantic model class for validating group broadcast messages,
                                      required when using send_group_message with kind="message"
    """

    # Authentication attributes
    authentication_classes: Sequence[type[BaseAuthentication]] | None = None
    permission_classes: (
        Sequence[type[BasePermission] | OperandHolder | SingleOperandHolder] | None
    ) = None
    queryset: QuerysetLike = True
    auth_method: Literal["get", "post", "put", "patch", "delete", "options"] = "get"
    lookup_field: str = "pk"
    lookup_url_kwarg: str | None = None

    authenticator_class: type[Any] = ChanxWebsocketAuthenticator

    # Message handling configuration
    send_completion: bool | None = None
    send_message_immediately: bool | None = None
    log_received_message: bool | None = None
    log_sent_message: bool | None = None
    log_ignored_actions: Iterable[str] | None = None
    send_authentication_message: bool | None = None

    # Message schemas
    INCOMING_MESSAGE_SCHEMA: type[BaseIncomingMessage]
    OUTGOING_GROUP_MESSAGE_SCHEMA: type[BaseOutgoingGroupMessage]

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
        # Initialize configuration from settings if not set
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

        # Create authenticator
        self.authenticator = self._create_authenticator()

        # Initialize instance attributes
        self.user: User | AnonymousUser | None = None
        self.obj: _M | None = None
        self.group_name: str | None = None
        self.connecting: bool = False

        if chanx_settings.CAMELIZE:
            if not humps:
                raise RuntimeError(MISSING_PYHUMPS_ERROR)

    def _create_authenticator(self) -> Any:
        """
        Create and configure the authenticator for this consumer.

        Returns:
            Configured authenticator instance
        """
        authenticator = self.authenticator_class()

        # Copy authentication attributes to the authenticator
        for attr in [
            "authentication_classes",
            "permission_classes",
            "queryset",
            "auth_method",
            "lookup_field",
            "lookup_url_kwarg",
        ]:
            if getattr(self, attr) is not None:
                setattr(authenticator, attr, getattr(self, attr))

        # Validate configuration during initialization
        authenticator.validate_configuration()

        return authenticator

    # Connection lifecycle methods

    async def websocket_connect(self, message: WebSocketConnectEvent) -> None:
        """
        Handle WebSocket connection request with authentication.

        Accepts the connection, authenticates the user, and either
        adds the user to appropriate groups or closes the connection.

        Args:
            message: The connection message from Channels
        """
        await self.accept()
        self.connecting = True

        # Authenticate the connection
        auth_result = await self.authenticator.authenticate(self.scope)

        # Store authentication results
        self.user = auth_result.user
        self.obj = auth_result.obj
        self.request = self.authenticator.request

        # Send authentication status if configured
        if self.send_authentication_message:
            await self.send_message(
                AuthenticationMessage(
                    payload=AuthenticationPayload(
                        status_code=auth_result.status_code,
                        status_text=auth_result.status_text,
                        data=auth_result.data,
                    )
                )
            )

        # Handle authentication result
        if auth_result.is_authenticated:
            await self.add_groups()
            await self.post_authentication()
        else:
            self.connecting = False
            await self.close()

    async def post_authentication(self) -> None:
        """
        Hook for additional actions after successful authentication.

        Subclasses can override this method to perform custom actions
        after a successful authentication.
        """
        pass

    async def add_groups(self) -> None:
        """
        Add the consumer to channel groups.

        Retrieves groups from build_groups() and adds this consumer
        to each channel group for broadcast messaging.

        """
        custom_groups = await self.build_groups()
        if self.groups:
            self.groups.extend(custom_groups)
        else:
            self.groups = custom_groups
        for group in self.groups:
            await self.channel_layer.group_add(group, self.channel_name)

    async def build_groups(self) -> list[str]:
        """
        Build list of channel groups to join.

        Subclasses should override this method to define which groups
        the consumer should join based on authentication results.

        Returns:
            Iterable of group names to join
        """
        return []

    async def websocket_disconnect(self, message: WebSocketDisconnectEvent) -> None:
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
        if chanx_settings.CAMELIZE:
            content = humps.decamelize(content)

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
        if chanx_settings.CAMELIZE:
            content = humps.camelize(content)

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

    # Group operations methods

    async def send_to_groups(
        self,
        content: dict[str, Any],
        groups: list[str] | None = None,
        *,
        exclude_current: bool = True,
        kind: Literal["json", "message"] = "json",
    ) -> None:
        """
        Send content to one or more channel groups.

        Low-level method to broadcast dictionary content to channel groups.
        For sending BaseMessage objects, prefer using send_group_message() instead.

        Args:
            content: Dictionary content to send to the groups
            groups: Group names to send to (defaults to self.groups)
            exclude_current: Whether to exclude the sending consumer from receiving
                            the broadcast (prevents echo effects)
            kind: Type of message to send:

                - "json": Send as raw JSON directly to clients (default)

                - "message": Process through OUTGOING_GROUP_MESSAGE_SCHEMA validation (requires consumer to define this schema)

        """
        if groups is None:
            groups = self.groups or []
        for group in groups:
            user_pk = getattr(self.user, "pk", None)

            await self.channel_layer.group_send(
                group,
                {
                    "type": "send_group_member",
                    "content": content,
                    "kind": kind,
                    "exclude_current": exclude_current,
                    "from_channel": self.channel_name,
                    "from_user_pk": user_pk,
                },
            )

    async def send_group_message(
        self,
        message: BaseMessage,
        groups: list[str] | None = None,
        *,
        kind: Literal["json", "message"] = "message",
        exclude_current: bool = True,
    ) -> None:
        """
        Send a BaseMessage object to one or more channel groups.

        Broadcasts a message to all consumers in the specified groups.
        This is useful for implementing pub/sub patterns where messages
        need to be distributed to multiple connected clients.

        Important:
            When using kind="message" (the default), your consumer class must define
            OUTGOING_GROUP_MESSAGE_SCHEMA to properly validate and wrap the message.
            This schema ensures that group messages follow the expected structure
            and contain the required metadata. If not defined, use kind="json" instead.

        Args:
            message: Message object to send to the groups
            groups: Group names to send to (defaults to self.groups)
            kind: Format to send the message as:

                  - "message": Validated and wrapped via OUTGOING_GROUP_MESSAGE_SCHEMA (default)

                  - "json": Sent as raw JSON without validation or wrapping
            exclude_current: Whether to exclude the sending consumer from receiving
                            the broadcast (prevents echo effects)
        """
        await self.send_to_groups(
            message.model_dump(),
            groups,
            kind=kind,
            exclude_current=exclude_current,
        )

    async def send_group_member(self, event: GroupMemberEvent) -> None:
        """
        Handle incoming group message and relay to client.

        Processes group messages from the channel layer, adds metadata like is_mine and is_current,
        and forwards to the client socket. This method is called by the Channels system when
        a message is sent to a group this consumer is part of.

        The method adds two metadata fields to all messages:

        - is_mine: True if the message originated from the current user

        - is_current: True if the message originated from this channel

        If the message is from the current channel and exclude_current is True, the message
        is not relayed to avoid echo effects. For message-type events, the content is wrapped
        in the OUTGOING_GROUP_MESSAGE_SCHEMA, while JSON-type events are sent directly.
        If configured, a GroupCompleteMessage is sent after successful processing.

        Args:
            event: Group member event data containing the content, kind, source channel,
                   user ID, and control flags
        """
        content = event["content"]
        exclude_current = event["exclude_current"]
        kind = event["kind"]
        from_channel = event["from_channel"]
        from_user_pk = event["from_user_pk"]

        if exclude_current and self.channel_name == from_channel:
            return

        user_pk = getattr(self.user, "pk", None)
        is_mine = bool(from_user_pk) and from_user_pk == user_pk

        content.update(
            {"is_mine": is_mine, "is_current": self.channel_name == from_channel}
        )

        if kind == "message":
            message = self.OUTGOING_GROUP_MESSAGE_SCHEMA.model_validate(
                {"group_message": content}
            ).group_message
            await self.send_message(message)
        else:
            await self.send_json(content)

        if self.send_completion:
            await self.send_message(GroupCompleteMessage())

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
