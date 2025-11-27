"""
Minimal channel-aware shared component detector.

Detects schemas and messages shared across multiple channels.
"""

from collections import defaultdict
from typing import cast

from chanx.asyncapi.type_defs import (
    AsyncAPIDocument,
    MessageObject,
    SchemaObject,
)


class SharedItemsAnalyzer:
    """
    Detects schemas and messages shared across multiple channels.

    After initialization:
    - shared_messages: list[MessageObject]
    - shared_schemas: list[SchemaObject]
    """

    def __init__(self, document: AsyncAPIDocument):
        self.document = document

        # Track which channels use each component (by id)
        schema_channels: dict[int, set[str]] = defaultdict(set)
        message_channels: dict[int, set[str]] = defaultdict(set)

        # Track id -> instance mapping
        schema_instances: dict[int, SchemaObject] = {}
        message_instances: dict[int, MessageObject] = {}

        # Get trackable schema IDs from components
        trackable_schema_ids: set[int] = set()
        if document.components and document.components.schemas:
            for schema in document.components.schemas.values():
                trackable_schema_ids.add(id(schema))

        # Analyze all channels
        if document.channels:
            for channel_name, channel in document.channels.items():
                if not channel.messages:
                    continue

                for message in channel.messages.values():
                    if not isinstance(message, MessageObject):
                        continue

                    # Track message
                    msg_id = id(message)
                    message_channels[msg_id].add(channel_name)
                    message_instances[msg_id] = message

                    # Track schemas in message payload
                    if message.payload:
                        self._track_schema_recursive(
                            message.payload,
                            channel_name,
                            trackable_schema_ids,
                            schema_channels,
                            schema_instances,
                        )

        # Compute final lists (only those in 2+ channels)
        self.shared_messages: list[MessageObject] = [
            message_instances[msg_id]
            for msg_id, channels in message_channels.items()
            if len(channels) > 1
        ]

        self.shared_schemas: list[SchemaObject] = [
            schema_instances[schema_id]
            for schema_id, channels in schema_channels.items()
            if len(channels) > 1
        ]

    def _track_schema_recursive(
        self,
        schema: SchemaObject,
        channel_name: str,
        trackable_schema_ids: set[int],
        schema_channels: dict[int, set[str]],
        schema_instances: dict[int, SchemaObject],
        visited: set[int] | None = None,
    ) -> None:
        """Recursively track schema usage."""
        if visited is None:
            visited = set()

        schema_id = id(schema)
        if schema_id in visited:
            return
        visited.add(schema_id)

        # Track if it's a component schema
        if schema_id in trackable_schema_ids:
            schema_channels[schema_id].add(channel_name)
            schema_instances[schema_id] = schema

        # Recurse into properties
        if schema.properties:
            for prop_schema in schema.properties.values():
                self._track_schema_recursive(
                    prop_schema,
                    channel_name,
                    trackable_schema_ids,
                    schema_channels,
                    schema_instances,
                    visited,
                )

        # Recurse into array items
        if schema.items and isinstance(schema.items, SchemaObject):
            self._track_schema_recursive(
                schema.items,
                channel_name,
                trackable_schema_ids,
                schema_channels,
                schema_instances,
                visited,
            )

        # Recurse into other schema fields (allOf, anyOf, oneOf, etc.)
        for field in ["allOf", "anyOf", "oneOf"]:
            value = getattr(schema, field, None)
            if value:
                if isinstance(value, list):
                    value = cast(list[SchemaObject], value)
                    for item in value:
                        self._track_schema_recursive(
                            item,
                            channel_name,
                            trackable_schema_ids,
                            schema_channels,
                            schema_instances,
                            visited,
                        )
                elif isinstance(value, SchemaObject):
                    self._track_schema_recursive(
                        value,
                        channel_name,
                        trackable_schema_ids,
                        schema_channels,
                        schema_instances,
                        visited,
                    )
