"""
Message registry and schema generation.

This module provides utilities to collect BaseMessage types from consumers
and generate JSON schemas. Originally used for AsyncAPI generation, but now
serves as the core message type registry for the chanx framework.
"""

from collections import defaultdict
from types import UnionType
from typing import Any, TypeAlias, Union, get_args, get_origin, get_type_hints

import humps
from chanx.asyncapi.type_defs import SchemaObject
from chanx.messages.base import BaseMessage
from pydantic import BaseModel

MessageSchema: TypeAlias = dict[str, Any]

MessageRef: TypeAlias = str
SchemaRef: TypeAlias = str

UNION_TYPES = (Union, UnionType)


def clean_consumer_name(consumer_name: str) -> str:
    """
    Remove 'Consumer' suffix from consumer class names.

    Args:
        consumer_name: The consumer class name to clean

    Returns:
        Consumer name without 'Consumer' suffix
    """
    return consumer_name.removesuffix("Consumer")


def get_asyncapi_schema_ref(schema_title: str) -> str:
    """
    Generate AsyncAPI schema reference path.

    Args:
        schema_title: The schema title to reference

    Returns:
        AsyncAPI schema reference string
    """
    return f"#/components/schemas/{schema_title}"


def get_asyncapi_message_ref(message_title: str) -> str:
    """
    Generate AsyncAPI message reference path.

    Args:
        message_title: The message title to reference

    Returns:
        AsyncAPI message reference string
    """
    return f"#/components/messages/{message_title}"


class MessageRegistry:
    """Registry for collecting and managing message types from consumers."""

    def __init__(self) -> None:
        self.schemas: dict[type[BaseModel], SchemaRef] = {}
        self.messages: dict[type[BaseMessage], MessageRef] = {}
        self._schema_names: set[str] = set()

        self.remap_schema_title: dict[type[BaseModel], str] = {}

        self.schema_objects: dict[str, dict[str, Any]] = {}
        self.message_objects: dict[str, dict[str, Any]] = {}
        self.consumer_messages = defaultdict[str, set[type[BaseMessage]]](
            set[type[BaseMessage]]
        )

    def build_message(
        self, message_type: type[BaseMessage], consumer_name: str
    ) -> None:
        """
        Build and register a message type in the registry.

        Args:
            message_type: The BaseMessage subclass to register
            consumer_name: Name of the consumer using this message type
        """
        self.consumer_messages[consumer_name].add(message_type)
        if message_type not in self.messages:
            message_title = self.remap_schema_title.get(
                message_type, message_type.__name__
            )
            message_name = humps.depascalize(message_title)

            message_schema = SchemaObject()
            message_schema.ref = self.schemas.get(message_type)

            self.message_objects[message_name] = {
                "payload": message_schema.model_dump(by_alias=True, exclude_none=True)
            }

            self.messages[message_type] = get_asyncapi_message_ref(message_name)

    def add(self, message_type: type[BaseMessage], consumer_name: str) -> None:
        """
        Add a message type to the registry, handling both simple types and unions.

        Args:
            message_type: The BaseMessage type or union to add
            consumer_name: Name of the consumer using this message type
        """
        self.build_message_schema(message_type, consumer_name)

        orig = get_origin(message_type)
        if orig in UNION_TYPES:
            for sub in get_args(message_type):
                if isinstance(sub, type) and issubclass(sub, BaseMessage):
                    self.build_message(sub, consumer_name)
        else:
            self.build_message(message_type, consumer_name)

    def _handle_union_type(
        self, model_type: type[BaseModel], consumer_name: str
    ) -> bool:
        """
        Handle Union/UnionType processing.

        Args:
            model_type: The model type to check for union
            consumer_name: Name of the consumer

        Returns:
            True if union contained BaseModel types
        """
        """Handle Union/UnionType processing. Returns True if union contained BaseModel types."""
        orig = get_origin(model_type)
        has_base = False
        if orig in UNION_TYPES:
            for sub in get_args(model_type):
                if isinstance(sub, type) and issubclass(sub, BaseModel):
                    has_base = True
                    self.build_message_schema(sub, consumer_name)
        return has_base

    def _update_schema_title(
        self,
        model_schema: dict[str, Any],
        model_type: type[BaseModel],
        consumer_name: str,
    ) -> None:
        """
        Update schema title if there's a naming conflict.

        Args:
            model_schema: The schema dictionary to update
            model_type: The model type being processed
            consumer_name: Name of the consumer
        """
        """Update schema title if there's a naming conflict."""
        if model_type.__name__ in self._schema_names:
            prefix = clean_consumer_name(consumer_name)
            retitle = prefix + model_schema["title"]
            model_schema["title"] = retitle
            self.remap_schema_title[model_type] = retitle

    def _process_field_types(
        self, model_type_fields: dict[str, Any], consumer_name: str
    ) -> tuple[set[str], dict[str, dict[int, type[BaseModel]]]]:
        """
        Process field types and return ref_fields and union_map.

        Args:
            model_type_fields: Dictionary of field names to types
            consumer_name: Name of the consumer

        Returns:
            Tuple of (ref_fields, union_map) for schema processing
        """
        """Process field types and return ref_fields and union_map."""
        ref_fields: set[str] = set()
        union_map: dict[str, dict[int, type[BaseModel]]] = {}

        for f_name, f_type in model_type_fields.items():
            if isinstance(f_type, type) and issubclass(f_type, BaseModel):
                self.build_message_schema(f_type, consumer_name)
                ref_fields.add(f_name)
                continue

            union_mapping = self._process_union_field(f_type, consumer_name)
            if union_mapping:
                union_map[f_name] = union_mapping

        return ref_fields, union_map

    def _process_union_field(
        self, f_type: Any, consumer_name: str
    ) -> dict[int, type[BaseModel]] | None:
        """
        Process a Union field type.

        Args:
            f_type: The union type to process
            consumer_name: Name of the consumer

        Returns:
            Mapping if it contains BaseModel types, None otherwise
        """
        """Process a Union field type. Returns mapping if it contains BaseModel types."""
        orig = get_origin(f_type)
        if orig in UNION_TYPES:
            mapping: dict[int, type[BaseModel]] = {}
            has_model = False
            for idx, item in enumerate(get_args(f_type)):
                if isinstance(item, type) and issubclass(item, BaseModel):
                    self.build_message_schema(item, consumer_name)
                    has_model = True
                    mapping[idx] = item
            return mapping if has_model else None
        return None

    def _update_schema_references(
        self,
        model_schema: dict[str, Any],
        ref_fields: set[str],
        union_map: dict[str, dict[int, type[BaseModel]]],
        model_type_fields: dict[str, Any],
    ) -> None:
        """
        Update schema with proper references.

        Args:
            model_schema: The schema to update
            ref_fields: Fields that need schema references
            union_map: Map of union field references
            model_type_fields: Original field type mapping
        """
        """Update schema with proper references."""
        model_schema.pop("$defs", None)
        properties = model_schema["properties"]

        if ref_fields:
            for ref in ref_fields:
                properties[ref] = {"$ref": self.schemas[model_type_fields[ref]]}

        if union_map:
            for ref_name, ref_map in union_map.items():
                field = properties[ref_name]["anyOf"]
                for idx, model in ref_map.items():
                    field[idx]["$ref"] = self.schemas[model]

    def build_message_schema(
        self, model_type: type[BaseModel], consumer_name: str
    ) -> None:
        """
        Build and register a JSON schema for a BaseModel type.

        Processes the model type, extracts field type information, handles unions,
        and generates proper schema references for AsyncAPI documentation.

        Args:
            model_type: The BaseModel type to process
            consumer_name: Name of the consumer using this type
        """
        # Handle Union types first
        if self._handle_union_type(model_type, consumer_name):
            return

        # Skip if already processed
        if model_type in self.schemas:
            return

        # Generate base schema
        model_schema = model_type.model_json_schema()
        self._update_schema_title(model_schema, model_type, consumer_name)

        # Process field types
        model_type_fields = get_type_hints(model_type)
        ref_fields, union_map = self._process_field_types(
            model_type_fields, consumer_name
        )

        # Update references
        self._update_schema_references(
            model_schema, ref_fields, union_map, model_type_fields
        )

        # Store the schema
        self.schemas[model_type] = get_asyncapi_schema_ref(model_schema["title"])
        self.schema_objects[model_schema["title"]] = model_schema
        self._schema_names.add(model_type.__name__)


message_registry = MessageRegistry()
