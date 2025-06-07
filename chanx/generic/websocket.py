"""
Authenticated WebSocket consumer system for Chanx.

This module provides the core WebSocket consumer implementation for Chanx,
offering a robust framework for building real-time applications with Django
Channels and Django REST Framework. The AsyncJsonWebsocketConsumer serves as the
foundation for WebSocket connections with integrated authentication, permissions,
structured message handling, group messaging capabilities, and typed channel events.

Key features:
- DRF-style authentication and permission checking
- Structured message handling with Pydantic validation
- Automatic group management for pub/sub messaging
- Typed channel event system
- Generic type parameters for compile-time type safety
- Comprehensive error handling and reporting
- Configurable logging and message completion signals
- Support for object-level permissions and retrieval

Generic Type System:
The consumer uses four generic type parameters for type safety:
- IC (Incoming): Union of BaseMessage subclasses for incoming messages
- Event (optional): Union of BaseChannelEvent subclasses for channel events
- M (optional): Model subclass for object-level permissions

Developers should subclass AsyncJsonWebsocketConsumer with appropriate generic parameters
and implement the receive_message method to handle incoming messages (and optionally
the receive_event method to handle channel events). The consumer automatically handles
connection lifecycle, authentication, message validation, and group messaging.
"""

import asyncio
import sys
import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from types import ModuleType
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypedDict,
    cast,
    get_args,
    get_origin,
)

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer as BaseAsyncJsonWebsocketConsumer,
)
from channels.layers import get_channel_layer
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Model
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import (
    BasePermission,
    OperandHolder,
    SingleOperandHolder,
)

import structlog
from asgiref.sync import async_to_sync
from asgiref.typing import WebSocketConnectEvent, WebSocketDisconnectEvent
from pydantic import Field, TypeAdapter, ValidationError
from typing_extensions import TypeVar, get_original_bases

from chanx.constants import MISSING_PYHUMPS_ERROR
from chanx.generic.authenticator import ChanxWebsocketAuthenticator, QuerysetLike
from chanx.messages.base import (
    BaseChannelEvent,
    BaseMessage,
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


IC = TypeVar("IC", bound=BaseMessage)  # Incoming messages
M = TypeVar("M", bound=Model | None, default=None)  # Object model
Event = TypeVar("Event", bound=BaseChannelEvent | None, default=None)  # Channel Events


class EventPayload(TypedDict):
    """
    Channel layer message containing event data.

    Attributes:
        event_data: Serialized event data dictionary
    """

    event_data: dict[str, Any]


class AsyncJsonWebsocketConsumer(
    Generic[IC, Event, M], BaseAsyncJsonWebsocketConsumer, ABC
):
    """
     Base class for asynchronous JSON WebSocket consumers with authentication and permissions.

    Provides DRF-style authentication/permissions, structured message handling with
    Pydantic validation, typed channel events, group messaging, logging, and error handling.
    Subclasses must implement `receive_message` and specify the incoming message type as
    a generic parameter.

    For typed channel events, subclasses can define a union type of channel events
    and use the Event generic parameter to enable type-safe channel event handling.
    Override the receive_event() method to process events sent via send_channel_event()
    or asend_channel_event(). Events are automatically validated against the Event
    type before being passed to your handler method.

    Generic Parameters:
        IC: Incoming message type (required) - Union of BaseMessage subclasses
        Event: Channel event type (optional) - Union of BaseChannelEvent subclasses or None
        M: Model type for object-level permissions (optional) - Model subclass or None

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
    _INCOMING_MESSAGE_SCHEMA: IC
    _EVENT_SCHEMA: Event

    # Object instance
    obj: M

    def __init_subclass__(cls, *args: Any, **kwargs: Any):
        """
        Validates and extracts generic type parameters during class definition.

        This method automatically extracts the generic type parameters (IC, Event, M)
        from the class definition and stores them for runtime use. It ensures that
        at least the incoming message type (IC) is specified.

        Handles differences between Python versions:
        - Python 3.10: Only returns non-default type arguments
        - Python 3.11+: Returns all type arguments including defaults

        Args:
            *args: Variable arguments passed to parent __init_subclass__
            **kwargs: Keyword arguments passed to parent __init_subclass__

        Raises:
            ValueError: If no generic parameters are specified (must specify at least IC)
        """
        super().__init_subclass__(*args, **kwargs)

        # Extract the actual type from Generic parameters
        orig_bases = get_original_bases(cls)
        for base in orig_bases:
            if base is AsyncJsonWebsocketConsumer:
                raise ValueError(
                    f"Class {cls.__name__!r} must specify at least the incoming message type as a generic parameter. "
                    f"Hint: class {cls.__name__}(AsyncJsonWebsocketConsumer[YourMessageType])"
                )
            if get_origin(base) is AsyncJsonWebsocketConsumer:
                # Workaround for TypeVar defaults handling differences across Python versions:
                # - In Python 3.10, get_args() only returns non-default types
                # - In Python 3.11+, get_args() returns all type arguments including defaults
                # We create a fixed-size array and populate it with available type arguments
                if sys.version_info < (3, 11):  # pragma: no cover
                    # Generic part of AsyncJsonWebsocketConsumer
                    generic_types = get_original_bases(AsyncJsonWebsocketConsumer)[0]
                    type_var_vals: list[Any] = [None] * len(get_args(generic_types))
                    for i, var in enumerate(get_args(base)):
                        if i < len(type_var_vals) and var is not None:
                            type_var_vals[i] = var

                    (
                        incoming_message_schema,
                        event_schema,
                        _model,
                    ) = type_var_vals
                else:
                    (
                        incoming_message_schema,
                        event_schema,
                        _model,
                    ) = get_args(base)
                cls._INCOMING_MESSAGE_SCHEMA = incoming_message_schema
                cls._EVENT_SCHEMA = event_schema
                break

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

        # Load configuration and validate
        self._load_configuration_from_settings()
        self._setup_message_adapters()

        # Create authenticator
        self.authenticator = self._create_authenticator()

        # Initialize instance attributes
        self._initialize_instance_attributes()

        # Validate optional dependencies
        self._validate_optional_dependencies()

    def _load_configuration_from_settings(self) -> None:
        """Load configuration values from settings if not already set."""
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

        if self.send_authentication_message is None:
            self.send_authentication_message = (
                chanx_settings.SEND_AUTHENTICATION_MESSAGE
            )

        # Process ignored actions
        self.ignore_actions: set[str] = (
            set(self.log_ignored_actions) if self.log_ignored_actions else set()
        )

    def _setup_message_adapters(self) -> None:
        """Set up Pydantic type adapters for message validation."""
        self.incoming_message_adapter: TypeAdapter[IC] = TypeAdapter(
            Annotated[
                self._INCOMING_MESSAGE_SCHEMA,
                Field(discriminator=chanx_settings.MESSAGE_ACTION_KEY),
            ]
        )

        self.event_adapter: TypeAdapter[Event] = TypeAdapter(
            Annotated[
                self._EVENT_SCHEMA,
                Field(discriminator="handler"),
            ]
        )

    def _initialize_instance_attributes(self) -> None:
        """Initialize instance attributes to their default values."""
        self.user: User | AnonymousUser | AbstractBaseUser | None = None
        self.group_name: str | None = None
        self.connecting: bool = False

    def _validate_optional_dependencies(self) -> None:
        """Validate that optional dependencies are available when needed."""
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
    async def receive_message(self, message: IC, **kwargs: Any) -> None:
        """
        Process a validated received message.

        Must be implemented by subclasses to handle messages after validation.
        The message parameter is automatically typed based on the IC generic parameter.

        Args:
            message: The validated message object (typed as IC)
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
        await self.send_json(message.model_dump(mode="json"))

    # Group operations methods

    async def send_to_groups(
        self,
        content: dict[str, Any],
        groups: list[str] | None = None,
        *,
        exclude_current: bool = True,
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
        Send a BaseMessage object to one or more channel groups.

        Broadcasts a message to all consumers in the specified groups.
        This is useful for implementing pub/sub patterns where messages
        need to be distributed to multiple connected clients.

        Args:
            message: Message object to send to the groups
            groups: Group names to send to (defaults to self.groups)

            exclude_current: Whether to exclude the sending consumer from receiving
                            the broadcast (prevents echo effects)
        """
        await self.send_to_groups(
            message.model_dump(mode="json"),
            groups,
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
        is not relayed to avoid echo effects. If configured, a GroupCompleteMessage is sent
        after successful processing.

        Args:
            event: Group member event data containing the content, kind, source channel,
                   user ID, and control flags
        """
        content = event["content"]
        exclude_current = event["exclude_current"]
        from_channel = event["from_channel"]
        from_user_pk = event["from_user_pk"]

        if exclude_current and self.channel_name == from_channel:
            return

        user_pk = getattr(self.user, "pk", None)
        is_mine = bool(from_user_pk) and from_user_pk == user_pk

        content.update(
            {"is_mine": is_mine, "is_current": self.channel_name == from_channel}
        )

        await self.send_json(content)

        if self.send_completion:
            await self.send_message(GroupCompleteMessage())

    # Channel event system methods
    @classmethod
    async def asend_channel_event(
        cls,
        group_name: str,
        event: Event,
    ) -> None:
        """
        Send a typed channel event to a channel group.

        This is a class method that provides a type-safe way to send events through
        the channel layer to consumers. It can be called from tasks, views, or other
        places where you don't have a consumer instance. The event type is constrained
        by the consumer's Event generic parameter.

        Args:
            group_name: Group name to send the event to
            event: The typed event to send (must match the consumer's Event type)
        """
        channel_layer = get_channel_layer()
        assert channel_layer is not None

        assert event is not None
        await channel_layer.group_send(
            group_name,
            {
                "type": "handle_channel_event",
                "event_data": event.model_dump(mode="json"),
            },
        )

    @classmethod
    def send_channel_event(
        cls,
        group_name: str,
        event: Event,
    ) -> None:
        """
        Synchronous version of asend_channel_event for use in Django tasks/views.

        This method provides the same functionality as asend_channel_event but
        can be called from synchronous code like Django tasks, views, or signals.

        Args:
            group_name: Group name to send to
            event: The typed event to send (constrained by the consumer's Event type)
        """
        async_to_sync(cls.asend_channel_event)(group_name, event)

    async def handle_channel_event(self, event_payload: EventPayload) -> None:
        """
        Internal dispatcher for typed channel events with completion signal.

        This method is called by the channel layer when an event is sent to a group
        this consumer belongs to. It validates the event data and forwards it to
        the receive_event method.

        Args:
            event_payload: The message from the channel layer containing event data

        """
        try:
            event_data_dict: dict[str, Any] = event_payload.get("event_data", {})
            event_data = self.event_adapter.validate_python(event_data_dict)

            assert event_data is not None

            await self.receive_event(event_data)

        except Exception:
            await logger.aexception("Failed to process channel event")
            # Don't re-raise to avoid breaking the channel layer
        finally:
            # Send completion signal if configured
            if self.send_completion:
                await self.send_message(CompleteMessage())

    async def receive_event(self, event: Event) -> None:
        """
        Process typed channel events received through the channel layer.

        This method is called when a channel event is sent to a group this consumer
        belongs to. Override this method to handle events sent via send_channel_event()
        or asend_channel_event().

        Channel events provide a way to send typed messages to consumers from outside
        the WebSocket connection (e.g., from Django views, tasks, or other consumers).
        Use pattern matching to handle different event types based on your Event
        generic parameter.

        Args:
            event: The validated event object (typed based on Event generic parameter)

        Note:
            This method is only called if your consumer defines the Event generic
            parameter. If Event is None, channel events are not supported.
        """

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

            message = self.incoming_message_adapter.validate_python(content)

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
