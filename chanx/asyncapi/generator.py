"""
AsyncAPI 3.0 specification generator for Chanx WebSocket consumers.

This module provides the AsyncAPIGenerator class that automatically generates
AsyncAPI documentation from Chanx WebSocket consumer routes and their decorated
handlers (@ws_handler, @event_handler, @channel).
"""

from textwrap import dedent
from types import UnionType
from typing import Any, cast, get_args

import humps

from chanx.asyncapi.constants import (
    DEFAULT_ASYNCAPI_TITLE,
    DEFAULT_ASYNCAPI_VERSION,
    DEFAULT_SERVER_PROTOCOL,
    DEFAULT_SERVER_URL,
)
from chanx.asyncapi.type_defs import ChannelObject, ParameterObject
from chanx.core.registry import message_registry
from chanx.core.websocket import AsyncJsonWebsocketConsumer
from chanx.messages.base import BaseMessage
from chanx.routing.discovery import RouteInfo
from chanx.type_defs import AsyncAPIHandlerInfo, ChannelInfo


class AsyncAPIGenerator:
    """
    Generates AsyncAPI 3.0 specifications from Chanx WebSocket routes.

    This class analyzes WebSocket consumer routes and their decorated handlers
    to automatically generate comprehensive AsyncAPI documentation including
    channels, operations, messages, and schemas.
    """

    def __init__(
        self,
        routes: list[RouteInfo],
        title: str | None = DEFAULT_ASYNCAPI_TITLE,
        version: str | None = DEFAULT_ASYNCAPI_VERSION,
        description: str | None = None,
        server_url: str | None = DEFAULT_SERVER_URL,
        server_protocol: str | None = DEFAULT_SERVER_PROTOCOL,
        camelize: bool | None = False,
    ):
        """
        Initialize the AsyncAPI generator with routes and metadata.

        Args:
            routes: List of WebSocket route information objects
            title: AsyncAPI document title
            version: AsyncAPI document version
            description: AsyncAPI document description
            server_url: Default server URL
            server_protocol: Default server protocol (ws/wss)
            camelize: Whether to convert all keys to camelCase (default: False)
        """
        self.routes = routes
        self.title = title
        self.version = version
        self.description = description
        self.server_url = server_url
        self.server_protocol = server_protocol
        self.camelize = camelize

        self.channels: dict[str, dict[str, Any]] = {}

        self._route_channel_mapping: dict[str, str] = {}

        self.operations: dict[str, dict[str, Any]] = {}

        self._operation_names: set[str] = set()

    def generate(self) -> dict[str, Any]:
        """
        Generate the complete AsyncAPI 3.0 specification.

        Builds channels and operations from the provided routes, then constructs
        the final AsyncAPI document with all components.

        Returns:
            Complete AsyncAPI 3.0 specification as a dictionary
        """
        self.build_channels()
        self.build_operations()

        spec = {
            "asyncapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "servers": {
                self._get_server_environment_name(): {
                    "host": self.server_url,
                    "protocol": self.server_protocol,
                }
            },
            "channels": self.channels,
            "operations": self.operations,
            "components": {
                "messages": dict(sorted(message_registry.message_objects.items())),
                "schemas": dict(sorted(message_registry.schema_objects.items())),
            },
        }

        # Apply camelization if enabled
        if self.camelize:
            spec = self._apply_camelization(spec)

        return spec

    def _get_server_environment_name(self) -> str:
        """
        Determine server environment name based on server URL.

        Returns 'development' for localhost/127.0.0.1, 'production' otherwise.
        """
        if not self.server_url:
            return "development"

        # Check for localhost indicators
        localhost_indicators = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            # Add IPv6 localhost
            "::1",
            "[::1]",
        ]

        for indicator in localhost_indicators:
            if indicator in self.server_url.lower():
                return "development"

        return "production"

    def build_channels(self) -> dict[str, dict[str, Any]]:
        """
        Build AsyncAPI channels from WebSocket routes.

        Analyzes each route and its consumer to create channel definitions
        including parameters, messages, and metadata from @channel decorators.

        Returns:
            Dictionary of channel name to channel specification
        """
        for route in self.routes:
            consumer = route.consumer

            # Check for @channel decorator metadata
            channel_info: ChannelInfo | dict[str, Any] = getattr(
                consumer, "_channel_info", {}
            )

            # Use decorator metadata or fallback to defaults
            channel_name: str = channel_info.get("name") or route.consumer.snake_name
            channel_description = channel_info.get(
                "description", dedent(str(route.consumer.__doc__))
            )

            channel = ChannelObject(
                address=route.channel_path,
                title=channel_name,
                description=channel_description,
            ).model_dump(exclude_none=True)
            if route.path_params:
                # Add path parameters to channel
                channel["parameters"] = {}
                for param_name, pattern in route.path_params.items():
                    # Get type description from Django converter or regex pattern
                    type_desc = self._get_parameter_type_description(pattern)

                    # Create parameter object following AsyncAPI Parameter Object spec
                    parameter = ParameterObject(
                        description=f"Path parameter for {param_name} ({type_desc})"
                    )

                    channel["parameters"][param_name] = parameter.model_dump(
                        exclude_none=True, by_alias=True
                    )

            channel["messages"] = self.get_channel_messages(consumer)

            # Add tags if specified in decorator
            if channel_info.get("tags"):
                channel["tags"] = [
                    {"name": tag} if isinstance(tag, str) else tag
                    for tag in channel_info.get("tags") or []
                ]

            # Use the resolved channel_name (which may be overridden by decorator)
            self.channels[channel_name] = channel
            self._route_channel_mapping[route.path] = channel_name

        return self.channels

    def get_channel_messages(
        self, consumer: type[AsyncJsonWebsocketConsumer]
    ) -> dict[str, dict[str, Any]]:
        """
        Extract message definitions for a channel from its consumer.

        Args:
            consumer: The WebSocket consumer class

        Returns:
            Dictionary mapping message names to message references
        """
        messages = message_registry.consumer_messages[consumer.__name__]
        channel_messages: dict[str, dict[str, Any]] = {}

        # Sort messages by class name for consistent ordering
        for message in sorted(messages, key=lambda m: m.__name__):
            message_name = message_registry.remap_schema_title.get(
                message, message.__name__
            )

            ref = {"$ref": message_registry.messages[message]}

            channel_messages[humps.decamelize(message_name)] = ref

        # Return sorted dictionary for consistent key ordering
        return dict(sorted(channel_messages.items()))

    def build_operations(self) -> None:
        """
        Build AsyncAPI operations from WebSocket and event handlers.

        Scans all consumers for @ws_handler and @event_handler decorated methods
        and creates corresponding send/receive operations with proper message
        references and reply definitions.
        """
        for route in self.routes:
            consumer = route.consumer

            for handler_info in consumer._MESSAGE_HANDLER_INFO_MAP.values():
                self._build_single_operation(
                    handler_info, consumer, route, is_event=False
                )

            # Build operations from event handlers (send operations)
            for _action, handler_info in consumer._EVENT_HANDLER_INFO_MAP.items():
                self._build_single_operation(
                    handler_info, consumer, route, is_event=True
                )

    def _build_single_operation(
        self,
        handler_info: AsyncAPIHandlerInfo,
        consumer: type[AsyncJsonWebsocketConsumer],
        route: RouteInfo,
        is_event: bool = False,
    ) -> None:
        """
        Build a receive operation from a WebSocket handler.

        Args:
            consumer: Consumer information object.
            handler_info: Handler information dictionary.

        Returns:
            AsyncAPI operation definition.
        """
        action_name = handler_info["action"]
        if action_name in self._operation_names:
            action_name = "_".join((consumer.snake_name, action_name))

        channel_name = self._route_channel_mapping[route.path]
        operation: dict[str, Any] = {
            "action": "receive" if not is_event else "send",
            "channel": {"$ref": f"#/channels/{channel_name}"},
            "description": handler_info.get("description") or "",
            "summary": handler_info.get("summary") or "",
        }

        # Add tags - convert to proper tag objects
        tags = handler_info.get("tags") or []
        if tags:
            operation["tags"] = [{"name": tag} for tag in tags]

        # Add input messages
        if not is_event:
            message_type = handler_info["input_type"]
            assert message_type
            message_name = (
                message_registry.remap_schema_title.get(message_type)
                or message_type.__name__
            )
            message_ref = humps.decamelize(message_name)

            operation["messages"] = [
                {"$ref": f"#/channels/{channel_name}/messages/{message_ref}"}
            ]

        # Add reply if there's an output type
        if handler_info["output_type"]:
            output_type = handler_info["output_type"]

            output_messages: list[dict[str, Any]] = []
            if isinstance(output_type, UnionType):
                for sub in get_args(output_type):
                    output_messages.append(self.build_output(channel_name, sub))
            else:
                output_messages.append(self.build_output(channel_name, output_type))

            if not is_event:
                operation["reply"] = {
                    "channel": {"$ref": f"#/channels/{channel_name}"},
                    "messages": output_messages,
                }
            else:
                operation["messages"] = output_messages

        self.operations[action_name] = operation
        self._operation_names.add(action_name)

    def build_output(
        self, channel_name: str, output_type: type[BaseMessage]
    ) -> dict[str, Any]:
        """
        Build an output message reference for operation responses.

        Args:
            channel_name: The channel name containing the message
            output_type: The BaseMessage subclass for the output

        Returns:
            Message reference dictionary for AsyncAPI specification
        """
        output_message_name = message_registry.remap_schema_title.get(
            output_type, output_type.__name__
        )
        output_message_ref = humps.decamelize(output_message_name)
        return {"$ref": f"#/channels/{channel_name}/messages/{output_message_ref}"}

    def _get_parameter_type_description(self, pattern: str) -> str:
        """
        Get parameter type description.

        Args:
            pattern: Django/Starlette converter type (int, str, slug, float, etc.) or regex pattern
        """
        # Check if it's a known converter type (Django or Starlette/FastAPI)
        if pattern in ["int", "str", "slug", "uuid", "path", "float"]:
            return pattern

        # For regex patterns, return with prefix
        return f"regex: {pattern}"

    def _camelize_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Camelize a JSON Schema object.

        This camelizes:
        - All property names in 'properties' and 'patternProperties'
        - All field references in 'required' array
        - All nested schema objects

        JSON Schema keywords are already in camelCase so they don't change.

        Args:
            schema: JSON Schema object

        Returns:
            Schema with camelized property names
        """
        # Use humps to camelize all keys recursively
        result = humps.camelize(schema)

        # Special handling for 'required' array - camelize the property name strings
        if "required" in schema and isinstance(schema["required"], list):
            required_items = cast(list[Any], schema["required"])  # type: ignore[redundant-cast]
            result["required"] = [
                humps.camelize(item) if isinstance(item, str) else item
                for item in required_items
            ]

        return result

    def _camelize_ref(self, ref: str) -> str:
        """
        Camelize component names in a $ref path.

        Schema names are kept as-is since they represent class names (PascalCase).
        Other names like channels, messages, and operations are camelized.

        Args:
            ref: Reference path like #/channels/channel_name/messages/message_name

        Returns:
            Reference with camelized component names (except schema names)
        """
        parts = ref.split("/")
        camelized_parts: list[str] = []

        # Track if the next part after "schemas" is a schema name
        schemas_keyword_index = -1
        if "schemas" in parts:
            schemas_keyword_index = parts.index("schemas")

        for i, part in enumerate(parts):
            # Don't camelize the first parts (#, channels, messages, operations, components, schemas)
            if i <= 1 or part in [
                "channels",
                "messages",
                "operations",
                "components",
                "schemas",
            ]:
                camelized_parts.append(part)
            # If this is the part immediately after "schemas", keep it as-is (schema/class name)
            elif schemas_keyword_index >= 0 and i == schemas_keyword_index + 1:
                camelized_parts.append(part)
            else:
                # Camelize other names (channels, messages, operations)
                camelized_parts.append(humps.camelize(part))

        return "/".join(camelized_parts)

    def _camelize_refs_in_dict(self, obj: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively camelize all $ref values in a dictionary.

        Args:
            obj: Dictionary to process

        Returns:
            Dictionary with camelized $ref values
        """
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key == "$ref" and isinstance(value, str):
                result[key] = self._camelize_ref(value)
            elif isinstance(value, dict):
                value = cast(dict[str, Any], value)
                result[key] = self._camelize_refs_in_dict(value)
            elif isinstance(value, list):
                value = cast(list[Any], value)  # type: ignore[redundant-cast]
                processed_list: list[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        item = cast(dict[str, Any], item)
                        processed_list.append(self._camelize_refs_in_dict(item))
                    else:
                        processed_list.append(item)
                result[key] = processed_list
            else:
                result[key] = value

        return result

    def _apply_camelization(self, spec: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
        """
        Apply camelization to the entire AsyncAPI spec.

        This includes:
        - Channel names
        - Operation names
        - Component message keys
        - Schema properties (in 'properties' field)
        - Schema required fields
        - $ref paths (except schema names which are kept as class names)

        Note: Schema keys themselves are NOT camelized as they represent
        class names (e.g., "NewUserMessage" stays as-is, not "newUserMessage").

        Args:
            spec: The AsyncAPI specification

        Returns:
            Camelized specification
        """
        result = spec.copy()

        # Camelize channel names and their message keys
        if "channels" in result:
            camelized_channels: dict[str, Any] = {}
            for channel_name, channel_spec in result["channels"].items():
                camel_name = humps.camelize(channel_name)
                camelized_channel = channel_spec.copy()

                # Camelize message keys within the channel
                if "messages" in camelized_channel:
                    camelized_channel_messages: dict[str, Any] = {}
                    for msg_key, msg_ref in camelized_channel["messages"].items():
                        camel_msg_key = humps.camelize(msg_key)
                        camelized_channel_messages[camel_msg_key] = msg_ref
                    camelized_channel["messages"] = camelized_channel_messages

                camelized_channels[camel_name] = camelized_channel
            result["channels"] = camelized_channels

        # Camelize operation names
        if "operations" in result:
            camelized_operations: dict[str, Any] = {}
            for op_name, op_spec in result["operations"].items():
                camel_name = humps.camelize(op_name)
                camelized_operations[camel_name] = op_spec
            result["operations"] = camelized_operations

        # Camelize component message keys
        if "components" in result and "messages" in result["components"]:
            camelized_messages: dict[str, Any] = {}
            for msg_key, msg_spec in result["components"]["messages"].items():
                camel_key = humps.camelize(msg_key)
                camelized_messages[camel_key] = msg_spec
            result["components"]["messages"] = camelized_messages

        # Camelize schema properties but keep schema keys as-is (they're class names in PascalCase)
        if "components" in result and "schemas" in result["components"]:
            camelized_schemas: dict[str, Any] = {}
            for schema_key, schema_spec in result["components"]["schemas"].items():
                # Keep schema key as-is (it's a class name like "NewUserMessage")
                # Only camelize the properties within the schema
                camelized_schema = self._camelize_schema(schema_spec)
                camelized_schemas[schema_key] = camelized_schema
            result["components"]["schemas"] = camelized_schemas

        # Camelize all $ref paths
        result = self._camelize_refs_in_dict(result)

        return result
