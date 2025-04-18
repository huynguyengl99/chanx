import asyncio
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import (
    Any,
    Generic,
    Literal,
    TypeVar,
    cast,
)

from channels.exceptions import InvalidChannelLayerError
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as BaseAsyncJsonWebsocketConsumer,
)
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Model
from django.http import HttpRequest
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import (
    BasePermission,
    OperandHolder,
    SingleOperandHolder,
)

import structlog
from pydantic import ValidationError

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

_MT_co = TypeVar("_MT_co", bound=Model, covariant=True)


class AsyncJsonWebsocketConsumer(BaseAsyncJsonWebsocketConsumer, Generic[_MT_co], ABC):  # type: ignore
    """
    Base class for asynchronous JSON WebSocket consumers with authentication and permissions.

    Provides DRF-style authentication/permissions, structured message handling with
    Pydantic validation, logging, and error handling. Subclasses must implement
    `receive_message` and set `INCOMING_MESSAGE_SCHEMA`.

    Attributes:
        authentication_classes: DRF authentication classes for connection verification
        permission_classes: DRF permission classes for connection authorization
        queryset: QuerySet or Manager used for retrieving objects
        auth_method: HTTP verb to emulate for authentication
        authenticator_class: Class to use for authentication
        send_completion: Whether to send completion message after processing
        send_message_immediately: Whether to yield control after sending messages
        log_received_message: Whether to log received messages
        log_sent_message: Whether to log sent messages
        log_ignored_actions: Message actions that should not be logged
        send_authentication_message: Whether to send auth status after connection
        INCOMING_MESSAGE_SCHEMA: Pydantic model class for message validation
        OUTGOING_GROUP_MESSAGE_SCHEMA: Pydantic model class for group messages
    """

    # Authentication attributes
    authentication_classes: Sequence[type[BaseAuthentication]] | None = None
    permission_classes: (
        Sequence[type[BasePermission] | OperandHolder | SingleOperandHolder] | None
    ) = None
    queryset: QuerysetLike = True
    auth_method: Literal["get", "post", "put", "patch", "delete", "options"] = "get"

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
        self.obj: _MT_co | None = None
        self.group_name: str | None = None
        self.connecting: bool = False
        self.request: HttpRequest | None = None

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
        ]:
            if hasattr(self, attr):
                setattr(authenticator, attr, getattr(self, attr))

        # Validate configuration during initialization
        authenticator.validate_configuration()

        return authenticator

    # Connection lifecycle methods

    async def websocket_connect(self, message: dict[str, Any]) -> None:
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
        self.obj = cast(_MT_co | None, auth_result.obj)
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

        Raises:
            InvalidChannelLayerError: If channel layer doesn't support groups
        """
        custom_groups = await self.build_groups()
        self.groups.extend(custom_groups)
        try:
            for group in self.groups:
                await self.channel_layer.group_add(group, self.channel_name)
        except AttributeError as e:
            raise InvalidChannelLayerError(
                "BACKEND is unconfigured or doesn't support groups"
            ) from e

    async def build_groups(self) -> Iterable[str]:
        """
        Build list of channel groups to join.

        Subclasses should override this method to define which groups
        the consumer should join based on authentication results.

        Returns:
            Iterable of group names to join
        """
        return []

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
        pass

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

        Args:
            content: Content to send
            groups: Group names to send to (defaults to self.groups)
            exclude_current: Whether to exclude the sending consumer
            kind: Type of message ('json' or 'message')
        """
        if groups is None:
            groups = self.groups
        for group in groups:
            user_pk = None
            if isinstance(self.user, User):
                user_pk = self.user.pk

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
        exclude_current: bool = True,
    ) -> None:
        """
        Send a BaseMessage object to one or more groups.

        Args:
            message: Message object to send
            groups: Group names to send to (defaults to self.groups)
            exclude_current: Whether to exclude the sending consumer
        """
        await self.send_to_groups(
            message.model_dump(),
            groups,
            kind="message",
            exclude_current=exclude_current,
        )

    async def send_group_member(self, event: GroupMemberEvent) -> None:
        """
        Handle incoming group message and relay to client.

        Processes group messages, adds metadata like is_mine and is_current,
        and forwards to the client socket.

        Args:
            event: Group member event data
        """
        content = event["content"]
        exclude_current = event["exclude_current"]
        kind = event["kind"]
        from_channel = event["from_channel"]
        from_user_pk = event["from_user_pk"]

        if exclude_current and self.channel_name == from_channel:
            return

        if kind == "message":
            is_mine = False
            if isinstance(self.user, User) and from_user_pk is not None:
                is_mine = self.user.pk == from_user_pk

            content.update(
                {"is_mine": is_mine, "is_current": self.channel_name == from_channel}
            )
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
