"""
Enhanced WebSocket consumer with automatic type generation and message routing.

This module provides the core AsyncJsonWebsocketConsumer class that extends
the base WebSocket consumer with automatic message type discovery, validation,
authentication, group broadcasting, and channel event handling capabilities.
"""

import asyncio
import uuid
from collections.abc import Callable, Collection
from functools import reduce
from types import UnionType
from typing import (
    Annotated,
    Any,
    ClassVar,
    Generic,
    cast,
    get_args,
    get_origin,
)

import humps
import structlog
from asgiref.sync import async_to_sync
from pydantic import Field, TypeAdapter, ValidationError
from typing_extensions import TypeVar

from chanx.constants import COMPLETE_ACTIONS
from chanx.core.authenticator import BaseAuthenticator
from chanx.core.config import config
from chanx.messages.base import BaseMessage
from chanx.messages.outgoing import (
    CompleteMessage,
    ErrorMessage,
    EventCompleteMessage,
    GroupCompleteMessage,
)
from chanx.type_defs import AsyncAPIHandlerInfo, EventPayload, GroupMessageEvent
from chanx.utils.asyncio import create_task
from chanx.utils.logging import logger

ReceiveEvent = TypeVar("ReceiveEvent", bound=BaseMessage, default=BaseMessage)


class ChanxWebsocketConsumerMixin(Generic[ReceiveEvent]):
    """
    Mixin providing enhanced WebSocket consumer functionality with automatic message routing.

    Provides automatic message type discovery from @ws_handler and @event_handler decorators,
    type-safe message validation using Pydantic discriminated unions, built-in authentication,
    group broadcasting, channel event system, and comprehensive error handling.
    """

    # Configuration attributes - can be overridden in subclasses
    send_completion: bool
    send_message_immediately: bool | None = config.send_message_immediately
    log_websocket_message: bool | None = config.log_websocket_message
    log_ignored_actions: Collection[str] = config.log_ignored_actions

    # Class-level configuration
    camelize: ClassVar[bool]
    discriminator_field: ClassVar[str] = (
        "action"  # Field used for message type discrimination
    )

    # Internal handler registries - populated automatically by metaclass
    _MESSAGE_HANDLER_INFO_MAP: dict[str, AsyncAPIHandlerInfo] = (
        {}
    )  # WebSocket message handlers
    _EVENT_HANDLER_INFO_MAP: dict[str, AsyncAPIHandlerInfo] = (
        {}
    )  # Channel event handlers

    # Authentication
    authenticator: BaseAuthenticator | None = None  # Active authenticator instance
    authenticator_class: type[BaseAuthenticator] | None = (
        None  # Authenticator class to instantiate
    )

    # Framework attributes (set by channels/fast-channels)
    scope: dict[str, Any]
    groups: list[str]  # Channel groups this consumer belongs to
    channel_layer: (
        Any  # Channel layer instance for group operations (framework-provided)
    )
    channel_name: str  # Unique channel name for this consumer instance
    channel_layer_alias: str

    # Auto-generated type adapters (built by metaclass)
    incoming_message_adapter: ClassVar[
        TypeAdapter[BaseMessage]
    ]  # Validates incoming messages
    incoming_event_adapter: ClassVar[
        TypeAdapter[BaseMessage]
    ]  # Validates incoming events
    outgoing_message_adapter: ClassVar[
        TypeAdapter[BaseMessage]
    ]  # Validates outgoing messages

    # Consumer identification (auto-generated from class name)
    name: ClassVar[str]  # Consumer name without "Consumer" suffix
    snake_name: ClassVar[str]  # Snake case version of consumer name

    get_channel_layer: Callable[[Any], Any]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Automatically build discriminated union from @ws_handler and @event_handler decorated methods.

        Called when a class inherits from AsyncJsonWebsocketConsumer. Scans for decorated methods,
        extracts message types, and builds type adapters for validation and routing.
        """
        super().__init_subclass__(**kwargs)

        cls.name = cls.__name__.removesuffix("Consumer")
        cls.snake_name = humps.decamelize(cls.name)

        # Skip if this is the abstract base class itself
        if cls.__name__ == "AbstractAsyncJsonWebsocketConsumer":
            return

        # Initialize handler info maps
        cls._MESSAGE_HANDLER_INFO_MAP = {}
        cls._EVENT_HANDLER_INFO_MAP = {}

        # Process all handlers
        cls._process_handlers()

    @classmethod
    def _process_handlers(cls) -> None:
        """
        Scan all methods in the class for handler decorators and process them.
        """
        # Scan all methods in the class (skip private/special attributes)
        for attr_name in dir(cls):
            # Skip private attributes and known problematic ones
            if attr_name.startswith("_") or attr_name in ("__abstractmethods__",):
                continue

            try:
                attr = getattr(cls, attr_name)
            except AttributeError:
                # Skip attributes that can't be accessed
                continue

            # Process WebSocket handlers
            if hasattr(attr, "_ws_handler_info"):
                ws_handler_info: AsyncAPIHandlerInfo = attr._ws_handler_info
                cls._MESSAGE_HANDLER_INFO_MAP[ws_handler_info["message_action"]] = (
                    ws_handler_info
                )

            # Process event handlers
            if hasattr(attr, "_event_handler_info"):
                event_handler_info: AsyncAPIHandlerInfo = attr._event_handler_info
                cls._EVENT_HANDLER_INFO_MAP[event_handler_info["message_action"]] = (
                    event_handler_info
                )

        # Extract types and build unions/adapters
        cls._build_adapters()

    @classmethod
    def _extract_types_from_handlers(
        cls, handler_info_map: dict[str, AsyncAPIHandlerInfo]
    ) -> tuple[list[type[BaseMessage]], list[type[BaseMessage]]]:
        """
        Extract input and output types from handler info map.

        Handles expansion of list/tuple/union types into individual types.

        Args:
            handler_info_map: Map of action -> AsyncAPIHandlerInfo

        Returns:
            Tuple of (input_types, output_types)
        """
        input_types: list[type[BaseMessage]] = []
        output_types: list[type[BaseMessage]] = []
        for info in handler_info_map.values():
            if info["input_type"]:
                input_types.append(info["input_type"])
            if info["output_type"]:
                output_type = info["output_type"]

                # Handle list/tuple of types - expand them
                if isinstance(output_type, list | tuple):
                    for msg_type in output_type:
                        output_types.append(msg_type)
                # Handle UnionType - expand into individual types
                elif get_origin(output_type) in (UnionType, type(None)):
                    for arg in get_args(output_type):
                        if isinstance(arg, type) and issubclass(arg, BaseMessage):
                            output_types.append(arg)
                # Handle single type
                else:
                    output_types.append(cast(type[BaseMessage], output_type))
        return input_types, output_types

    @classmethod
    def _create_adapter(
        cls, union_type: BaseMessage, discriminator_field: str
    ) -> TypeAdapter[BaseMessage]:
        """
        Create TypeAdapter for a discriminated union type.

        Args:
            union_type: The discriminated union type
            discriminator_field: Field name for discrimination

        Returns:
            TypeAdapter for message validation
        """
        return TypeAdapter(
            Annotated[
                union_type,
                Field(discriminator=discriminator_field),
            ]
        )

    @classmethod
    def _build_adapters(cls) -> None:
        """
        Extract input/output types from handlers and build unions and adapters.
        """
        # Extract types from both handler maps
        message_input_types, message_output_types = cls._extract_types_from_handlers(
            cls._MESSAGE_HANDLER_INFO_MAP
        )
        event_input_types, event_output_types = cls._extract_types_from_handlers(
            cls._EVENT_HANDLER_INFO_MAP
        )

        incoming_message_union = cls._create_discriminated_union(
            message_input_types, cls.discriminator_field
        )
        cls.incoming_message_adapter = cls._create_adapter(
            incoming_message_union, cls.discriminator_field
        )

        incoming_event_union = cls._create_discriminated_union(
            event_input_types, cls.discriminator_field
        )
        cls.incoming_event_adapter = cls._create_adapter(
            incoming_event_union, cls.discriminator_field
        )

        all_output_types = set(message_output_types + event_output_types)
        all_output_types |= {
            CompleteMessage,
            GroupCompleteMessage,
            EventCompleteMessage,
            ErrorMessage,
        }

        outgoing_union = cls._create_discriminated_union(
            list(all_output_types), cls.discriminator_field
        )
        cls.outgoing_message_adapter = cls._create_adapter(
            outgoing_union, cls.discriminator_field
        )

    @classmethod
    def _create_discriminated_union(
        cls, message_types: list[type[BaseMessage]] | None, discriminator_field: str
    ) -> Any:
        """
        Create a discriminated union from a list of message types.

        Args:
            message_types: List of BaseMessage subclasses to union
            discriminator_field: The field name to use for discrimination

        Returns:
            A discriminated union type that can validate any of the input message types
        """
        if message_types is None:
            return None

        if len(message_types) == 1:
            # If only one message type, return it directly
            return message_types[0]

        # Create annotated type with configurable discriminator field
        # Convert list to Union type for proper type annotation
        union_type = (
            reduce(lambda a, b: a | b, message_types) if message_types else None  # type: ignore
        )
        discriminated_union = Annotated[
            union_type, Field(discriminator=discriminator_field)  # type: ignore[valid-type]
        ]

        return discriminated_union

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.authenticator_class:
            self.authenticator = self.authenticator_class(self.send_message)

    @property
    def should_send_completion(self) -> bool:
        """
        Determine whether completion messages should be sent after handling requests.

        Checks for instance-level send_completion attribute first, then falls back
        to global configuration setting.

        Returns:
            True if completion messages should be sent, False otherwise
        """
        if hasattr(self, "send_completion"):
            return self.send_completion
        return config.send_completion

    @property
    def should_camelize(self) -> bool:
        """
        Determine whether message field names should be camelized.

        Checks for instance-level camelize attribute first, then falls back
        to global configuration setting. When True, snake_case field names
        are converted to camelCase in outgoing messages.

        Returns:
            True if field names should be camelized, False otherwise
        """
        if hasattr(self, "camelize"):
            return self.camelize
        return config.camelize

    @property
    def all_log_ignored_actions(self) -> set[str]:
        """
        Get the complete set of actions that should be ignored during logging.

        Combines instance-specific log_ignored_actions with system-level
        COMPLETE_ACTIONS to create the full set of actions to exclude
        from logging.

        Returns:
            Set of action names that should not be logged
        """
        return set(self.log_ignored_actions) | COMPLETE_ACTIONS

    async def websocket_connect(self, message: Any) -> None:
        """
        Handle WebSocket connection request with authentication.

        Accepts the connection, authenticates the user, and either
        adds the user to appropriate groups or closes the connection.

        Args:
            message: The connection message from the framework
        """
        await self.accept()  # type: ignore

        # Authenticate the connection
        if self.authenticator:
            auth_result = await self.authenticator.authenticate(self.scope)

            if not auth_result:
                await self.close()  # type: ignore
                return

        try:
            for group in self.groups:
                channel_layer = self.__class__.get_channel_layer(
                    self.channel_layer_alias
                )
                if channel_layer:
                    await channel_layer.group_add(group, self.channel_name)
        except AttributeError:
            raise ValueError(
                "BACKEND is unconfigured or doesn't support groups"
            ) from None

        await self.post_authentication()

    async def websocket_disconnect(self, message: Any) -> None:
        """
        Handle WebSocket disconnection.

        Cleans up context variables and logs the disconnection.

        Args:
            message: The disconnection message from the framework
        """
        await logger.ainfo("Disconnecting websocket")
        structlog.contextvars.clear_contextvars()
        await super().websocket_disconnect(message)  # type: ignore

    async def post_authentication(self) -> None:
        """
        Hook for additional actions after successful authentication.

        Subclasses can override this method to perform custom actions
        after a successful authentication.
        """
        pass

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """
        Receive and process JSON data from WebSocket.

        Logs messages, assigns ID, and creates task for async processing. Also enhances
        asyncio context with message id and message action.

        Args:
            content: The JSON content received from the client
            **kwargs: Additional keyword arguments
        """
        if self.should_camelize:
            content = humps.decamelize(content)

        message_action = content.get(self.discriminator_field)

        message_id = str(uuid.uuid4())[:8]
        token = structlog.contextvars.bind_contextvars(
            message_id=message_id, received_action=message_action
        )

        if (
            self.log_websocket_message
            and message_action not in self.all_log_ignored_actions
        ):
            await logger.ainfo("Websocket received")

        create_task(self.handle_json(content, **kwargs))
        structlog.contextvars.reset_contextvars(**token)

    async def handle_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """
        Handle received JSON message with validation and routing.

        Validates incoming messages using auto-generated discriminated union,
        routes to appropriate handlers, and sends error responses on failure.

        Args:
            content: The JSON content to handle
            **kwargs: Additional keyword arguments
        """
        try:
            message = self.incoming_message_adapter.validate_python(content)
            await self.receive_message(message)

        except ValidationError as e:
            await self.handle_validation_error(e)
        except Exception as e:
            await self.handle_json_processing_error(e)

        # Send completion signal if configured
        if self.should_send_completion:
            await self.send_message(CompleteMessage())

    async def receive_message(self, message: BaseMessage) -> None:
        """
        Process a validated received message and route it to the appropriate handler.

        Args:
            message: The validated message object (BaseMessage instance)
        """
        # Extract the action from the discriminator field
        message_action = getattr(message, self.discriminator_field)

        # Find the handler for this message_action
        handler_info = self.__class__._MESSAGE_HANDLER_INFO_MAP[message_action]

        # Get the handler method by name
        method_name = handler_info["method_name"]
        handler_method = getattr(self, method_name)

        try:
            # Call the handler method with the validated message
            result = await handler_method(message)

            # If handler returns something, we could send it back (optional)
            if result is not None:
                await self.handle_result(result)

        except Exception as e:
            await self.handle_message_handler_error(e, message_action, message)

    async def handle_result(self, result: BaseMessage) -> None:
        """
        Process and send the result returned by a message handler.

        Args:
            result: The result returned by the handler (BaseMessage)
        """
        # Convert result to JSON-serializable format
        await self.send_message(result)

    async def send_message(
        self, message: BaseMessage, *, validate: bool = False
    ) -> None:
        """
        Send a BaseMessage to the client.

        Args:
            message: The BaseMessage instance to send
            validate: Whether to validate the message against the outgoing adapter
        """
        # Optionally validate outgoing message
        if validate and self.__class__.outgoing_message_adapter:
            try:
                self.__class__.outgoing_message_adapter.validate_python(
                    message.model_dump(mode="json")
                )
            except ValidationError as e:
                await logger.aexception(f"Outgoing message validation failed: {e}")
                raise

        # Convert message to JSON and send
        json_data = message.model_dump(mode="json")

        # Apply camelization if enabled
        if self.should_camelize:
            json_data = humps.camelize(json_data)

        await self.send_json(json_data)

    async def send_json(self, content: dict[str, Any], close: bool = False) -> None:
        """
        Send JSON data to the client.

        Args:
            content: The JSON data to send
            close: Whether to close the connection after sending
        """
        await super().send_json(content, close)  # type: ignore

        message_action = content.get(self.discriminator_field)
        if (
            self.log_websocket_message
            and message_action not in self.all_log_ignored_actions
        ):
            await logger.ainfo("Websocket sent", sent_action=message_action)
        if self.send_message_immediately:
            await asyncio.sleep(0)

    async def handle_message_handler_error(
        self, error: Exception, action: str, message: BaseMessage
    ) -> None:
        """
        Handle errors that occur in message handlers.

        Args:
            error: The exception that occurred
            action: The action that was being handled
            message: The message that caused the error
        """
        # Default implementation - subclasses can override
        await self.send_message(
            ErrorMessage(payload={"detail": f"Failed to process message for {action}"})
        )
        await logger.aexception(f"Handler error for action '{action}': {error}")

    # Group operations methods
    async def broadcast_message(
        self,
        message: BaseMessage | dict[str, Any],
        groups: list[str] | None = None,
        *,
        exclude_current: bool = False,
    ) -> None:
        """
        Send a BaseMessage object to one or more channel groups.

        Broadcasts a message to all consumers in the specified groups.
        This is useful for implementing pub/sub patterns where messages
        need to be distributed to multiple connected clients.

        Args:
            message: Message object to send to the groups.
            groups: Group names to send to (defaults to self.groups)

            exclude_current: Whether to exclude the sending consumer from receiving
                            the broadcast (prevents echo effects)
        """
        channel_layer = self.__class__.get_channel_layer(self.channel_layer_alias)
        assert channel_layer

        if groups is None:
            groups = self.groups or []

        if isinstance(message, BaseMessage):
            message = message.model_dump(mode="json")

        for group in groups:
            await channel_layer.group_send(
                group,
                {
                    "type": "handle_group_message",
                    "message": message,
                    "exclude_current": exclude_current,
                    "from_channel": self.channel_name,
                },
            )

    async def handle_group_message(self, event: GroupMessageEvent) -> None:
        """
        Handle incoming group message and relay to client.

        Processes group messages from the channel layer, adds metadata (is_current),
        and forwards to the client. Respects exclude_current flag to prevent echo effects.

        Args:
            event: Group message event containing message data and metadata
        """
        message = event["message"]
        exclude_current = event["exclude_current"]
        from_channel = event["from_channel"]

        if exclude_current and self.channel_name == from_channel:
            return

        await self.send_json(message)

        if self.should_send_completion:
            await self.send_message(GroupCompleteMessage())

    # Channel event system methods
    @classmethod
    async def send_event(
        cls,
        event: ReceiveEvent,
        channel_name: str,
    ) -> None:
        """
        Send a typed channel event to a specific channel.

        Args:
            event: The typed event to send (BaseMessage subclass)
            channel_name: Channel name to send the event to
        """
        channel_layer = cls.get_channel_layer(cls.channel_layer_alias)
        assert channel_layer is not None

        await channel_layer.send(
            channel_name,
            {
                "type": "handle_channel_event",
                "event_data": event.model_dump(mode="json"),
            },
        )

    @classmethod
    def send_event_sync(
        cls,
        event: ReceiveEvent,
        channel_name: str,
    ) -> None:
        """
        Synchronous version of send_event for use in sync contexts.

        Args:
            event: The typed event to send (BaseMessage subclass)
            channel_name: Channel name to send to
        """
        async_to_sync(cls.send_event)(event, channel_name)

    @classmethod
    async def broadcast_event(
        cls,
        event: ReceiveEvent,
        groups: Collection[str] | str | None = None,
    ) -> None:
        """
        Broadcast a typed channel event to channel groups.

        Args:
            event: The typed event to broadcast (BaseMessage subclass)
            groups: Groups to broadcast the event to
        """
        channel_layer = cls.get_channel_layer(cls.channel_layer_alias)
        assert channel_layer is not None
        group_list: list[str]
        if groups is None:
            group_list = cls.groups or []
        elif isinstance(groups, str):
            group_list = [groups]
        else:
            group_list = list(groups)

        for group in group_list:
            await channel_layer.group_send(
                group,
                {
                    "type": "handle_channel_event",
                    "event_data": event.model_dump(mode="json"),
                },
            )

    @classmethod
    def broadcast_event_sync(
        cls,
        event: ReceiveEvent,
        groups: Collection[str] | str | None = None,
    ) -> None:
        """
        Synchronous version of broadcast_event for use in sync contexts.

        Args:
            event: The typed event to broadcast (BaseMessage subclass)
            groups: Groups to broadcast to
        """
        async_to_sync(cls.broadcast_event)(event, groups)

    async def handle_channel_event(self, event_payload: EventPayload) -> None:
        """
        Internal dispatcher for typed channel events with completion signal.

        This method is called by the channel layer when an event is sent to a group
        this consumer belongs to. It validates the event data and routes it to
        the appropriate @event_handler decorated method.

        Args:
            event_payload: The message from the channel layer containing event data
        """
        try:
            event_data_dict: dict[str, Any] = event_payload.get("event_data", {})
            event = self.incoming_event_adapter.validate_python(event_data_dict)

            assert event is not None

            await self.receive_event(event)

        except ValidationError as e:
            # Log validation error for channel events
            await logger.aexception(f"Channel event validation failed: {e}")
        except Exception:
            await logger.aexception("Failed to process channel event")

    async def receive_event(self, event: BaseMessage) -> None:
        """
        Process channel events received through the channel layer.

        Routes events to @event_handler decorated methods based on action field.

        Args:
            event: The validated event object
        """

        # Extract the action from the event
        action = getattr(event, "action", None)

        if not action:
            await logger.aerror("Event missing action field")
            return

        # Find the handler for this action
        event_handler_info = self.__class__._EVENT_HANDLER_INFO_MAP[action]

        # Get the handler method by name
        method_name = event_handler_info["method_name"]
        handler_method = getattr(self, method_name)

        try:
            # Call the handler method with the validated event
            result = await handler_method(event)

            # Events are received through channel system, so send event completion
            if result is not None:
                await self.send_message(result)

        except Exception as e:
            await self.handle_event_handler_error(e, action, event)

        if self.should_send_completion:
            await self.send_message(EventCompleteMessage())

    async def handle_validation_error(self, error: ValidationError) -> None:
        """
        Handle ValidationError exceptions during message processing.

        Subclasses can override this method to customize validation error responses.

        Args:
            error: The ValidationError that occurred
        """
        await self.send_message(
            ErrorMessage(
                payload=error.errors(
                    include_url=False, include_context=False, include_input=False
                )
            )
        )

    async def handle_json_processing_error(self, error: Exception) -> None:
        """
        Handle general exceptions during JSON message processing.

        Subclasses can override this method to customize error responses.

        Args:
            error: The exception that occurred
        """
        await self.send_message(
            ErrorMessage(payload={"detail": "Failed to process message"})
        )
        # Log the actual error for debugging
        await logger.aexception(f"Failed to process message: {str(error)}")

    async def handle_event_handler_error(
        self, error: Exception, action: str, event: BaseMessage
    ) -> None:
        """
        Handle errors that occur in event handlers.

        Args:
            error: The exception that occurred
            action: The action that was being processed
            event: The event that caused the error
        """
        await logger.aexception(f"Event handler error for action '{action}': {error}")
