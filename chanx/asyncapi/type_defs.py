"""
AsyncAPI 3.0 data models for specification generation with $ref resolution.

This module contains Pydantic models representing all AsyncAPI 3.0 specification
objects including schemas, messages, operations, channels, and the root document.
These models support automatic resolution of $ref pointers to actual instances.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, model_validator


# -------------------------
# Reusable / Common Objects
# -------------------------
class ContactObject(BaseModel):
    """AsyncAPI Contact Object for API contact information."""

    name: str | None = None
    url: str | None = None
    email: str | None = None


class LicenseObject(BaseModel):
    """AsyncAPI License Object for API license information."""

    name: str | None = None
    url: str | None = None


class ExternalDocumentationObject(BaseModel):
    """AsyncAPI External Documentation Object for referencing external documentation."""

    description: str | None = None
    url: str | None = None


class TagObject(BaseModel):
    """AsyncAPI Tag Object for API categorization and grouping."""

    name: str
    description: str | None = None
    externalDocs: ExternalDocumentationObject | None = None


# -------------------------
# Schema Object (JSON Schema subset)
# -------------------------
class SchemaObject(BaseModel):
    """AsyncAPI Schema Object representing JSON Schema subset for message payloads."""

    # `$ref` aliasing for JSON/YAML output
    ref: str | None = Field(default=None, alias="$ref")

    title: str | None = None
    description: str | None = None

    # type system
    type: str | list[str] | None = None
    format: str | None = None
    default: Any | None = None
    enum: list[Any] | None = None
    const: Any | None = None
    multipleOf: int | float | None = None
    maximum: int | float | None = None
    exclusiveMaximum: int | float | None = None
    minimum: int | float | None = None
    exclusiveMinimum: int | float | None = None
    maxLength: int | None = None
    minLength: int | None = None
    pattern: str | None = None

    # arrays
    items: SchemaObject | list[SchemaObject] | None = None
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool | None = None
    contains: SchemaObject | None = None
    prefixItems: list[SchemaObject] | None = None

    # objects
    maxProperties: int | None = None
    minProperties: int | None = None
    required: list[str] | None = None
    properties: dict[str, SchemaObject] | None = None
    patternProperties: dict[str, SchemaObject] | None = None
    additionalProperties: SchemaObject | bool | None = None
    propertyNames: SchemaObject | None = None
    unevaluatedProperties: SchemaObject | bool | None = None

    # composition
    allOf: list[SchemaObject] | None = None
    anyOf: list[SchemaObject] | None = None
    oneOf: list[SchemaObject] | None = None

    # JSON Schema keywords that are Python reserved words — use aliases for serialization
    not_: SchemaObject | None = Field(default=None, alias="not")
    if_: SchemaObject | None = Field(default=None, alias="if")
    then: SchemaObject | None = None
    else_: SchemaObject | None = Field(default=None, alias="else")
    dependentSchemas: dict[str, SchemaObject] | None = None

    # annotations
    deprecated: bool | None = None
    examples: list[Any] | None = None

    class Config:
        """Pydantic configuration for SchemaObject to support alias field names."""

        populate_by_name = True


# -------------------------
# Server Objects & Bindings
# -------------------------
class ServerVariableObject(BaseModel):
    """AsyncAPI Server Variable Object for parameterized server values."""

    enum: list[str] | None = None
    default: str
    description: str | None = None


class ServerObject(BaseModel):
    """AsyncAPI Server Object describing a server where the API is hosted."""

    url: str | None = None
    host: str | None = None
    protocol: str | None = None
    protocolVersion: str | None = None
    pathname: str | None = None
    description: str | None = None
    title: str | None = None
    summary: str | None = None
    security: list[dict[str, list[str]]] | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    bindings: dict[str, dict[str, Any]] | None = None
    variables: dict[str, ServerVariableObject] | None = None


# -------------------------
# Message & Traits & Bindings
# -------------------------
class CorrelationIdObject(BaseModel):
    """AsyncAPI Correlation ID Object for message correlation."""

    description: str | None = None
    location: str | None = None


class MessageTraitObject(BaseModel):
    """AsyncAPI Message Trait Object defining reusable message characteristics."""

    schemaFormat: str | None = None
    contentType: str | None = None
    headers: SchemaObject | None = None
    correlationId: CorrelationIdObject | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    bindings: dict[str, dict[str, Any]] | None = None


class MessageObject(BaseModel):
    """AsyncAPI Message Object describing a message payload and metadata."""

    ref: str | None = Field(default=None, alias="$ref")

    name: str | None = None
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    contentType: str | None = None
    schemaFormat: str | None = None
    headers: SchemaObject | None = None
    payload: SchemaObject | None = None
    correlationId: CorrelationIdObject | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    bindings: dict[str, dict[str, Any]] | None = None
    traits: list[MessageTraitObject | dict[str, Any]] | None = None

    class Config:
        """Pydantic configuration for MessageObject to support alias field names."""

        populate_by_name = True


# -------------------------
# Reply Object (operation.reply)
# -------------------------
class ReplyAddressObject(BaseModel):
    """AsyncAPI Reply Address Object for operation reply addressing."""

    location: str | None = None
    description: str | None = None


class OperationReplyObject(BaseModel):
    """AsyncAPI Operation Reply Object for defining operation responses."""

    address: ReplyAddressObject | None = None
    channel: dict[str, Any] | None = None
    messages: list[MessageObject] | None = None


# -------------------------
# Operation & Traits & Bindings
# -------------------------
class OperationTraitObject(BaseModel):
    """AsyncAPI Operation Trait Object for reusable operation characteristics."""

    summary: str | None = None
    description: str | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    bindings: dict[str, dict[str, Any]] | None = None


class OperationObject(BaseModel):
    """AsyncAPI Operation Object describing send/receive operations on channels."""

    action: str | None = None
    channel: dict[str, Any] | None = None
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    security: list[dict[str, list[str]]] | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    bindings: dict[str, dict[str, Any]] | None = None
    traits: list[OperationTraitObject | dict[str, Any]] | None = None
    messages: list[MessageObject | dict[str, Any]] | None = None
    reply: OperationReplyObject | None = None


# -------------------------
# Channel Object & Bindings
# -------------------------
class ParameterObject(BaseModel):
    """AsyncAPI Parameter Object for channel address parameters."""

    enum: list[str] | None = None
    default: str | None = None
    description: str | None = None
    examples: list[str] | None = None
    location: str | None = None

    class Config:
        """Pydantic configuration for ParameterObject to support alias field names."""

        populate_by_name = True


class ChannelObject(BaseModel):
    """AsyncAPI Channel Object describing a communication channel."""

    address: str | None = None
    title: str
    summary: str | None = None
    description: str | None = None
    servers: list[str] | None = None
    parameters: dict[str, ParameterObject] | None = None
    messages: dict[str, MessageObject | dict[str, Any]] | None = None
    bindings: dict[str, dict[str, Any]] | None = None
    subscribe: OperationObject | None = None
    publish: OperationObject | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None


# -------------------------
# Components Object (reusable definitions)
# -------------------------
class ComponentsObject(BaseModel):
    """AsyncAPI Components Object for reusable specification elements."""

    schemas: dict[str, SchemaObject] | None = None
    servers: dict[str, ServerObject] | None = None
    channels: dict[str, ChannelObject] | None = None
    operations: dict[str, OperationObject] | None = None
    messages: dict[str, MessageObject] | None = None
    securitySchemes: dict[str, dict[str, Any]] | None = None
    serverVariables: dict[str, ServerVariableObject] | None = None
    parameters: dict[str, ParameterObject] | None = None
    correlationIds: dict[str, CorrelationIdObject] | None = None
    replies: dict[str, OperationReplyObject] | None = None
    replyAddresses: dict[str, ReplyAddressObject] | None = None
    externalDocs: dict[str, ExternalDocumentationObject] | None = None
    tags: dict[str, TagObject] | None = None
    operationTraits: dict[str, OperationTraitObject] | None = None
    messageTraits: dict[str, MessageTraitObject] | None = None
    serverBindings: dict[str, dict[str, Any]] | None = None
    channelBindings: dict[str, dict[str, Any]] | None = None
    operationBindings: dict[str, dict[str, Any]] | None = None
    messageBindings: dict[str, dict[str, Any]] | None = None


# -------------------------
# Info Object & Root AsyncAPI Document
# -------------------------
class InfoObject(BaseModel):
    """AsyncAPI Info Object containing API metadata."""

    title: str
    version: str
    description: str | None = None
    termsOfService: str | None = None
    contact: ContactObject | None = None
    license: LicenseObject | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None


# -------------------------
# Reference Resolver
# -------------------------
class ReferenceResolver:
    """
    Handles resolution of $ref pointers in an AsyncAPI document.

    This class is responsible for traversing the document tree and
    replacing $ref references with their actual target objects.
    """

    def __init__(self, document: AsyncAPIDocument) -> None:
        """
        Initialize the resolver with a document.

        Args:
            document: The AsyncAPI document to resolve references in.
        """
        self._document = document
        self._visited: set[int] = set()

    def resolve_all(self) -> None:
        """Resolve all $ref references in the document."""
        self._visited.clear()
        self._resolve_recursive(self._document)

    def _resolve_recursive(self, obj: Any) -> Any:
        """
        Recursively resolve $ref references in the object tree.

        Args:
            obj: The object to process (BaseModel, dict, list, or primitive)

        Returns:
            The object with all $ref references resolved, or a replacement object
        """
        # Skip None and primitives
        if obj is None or isinstance(obj, str | int | float | bool):
            return obj

        # Prevent infinite loops with circular references
        obj_id = id(obj)
        if obj_id in self._visited:
            return obj
        self._visited.add(obj_id)

        if isinstance(obj, BaseModel):
            return self._resolve_model(obj)
        elif isinstance(obj, dict):
            return self._resolve_dict(cast(dict[str, Any], obj))
        elif isinstance(obj, list):
            return self._resolve_list(cast(list[Any], obj))  # type: ignore[redundant-cast]

        return obj

    def _resolve_model(self, model: BaseModel) -> BaseModel | Any:
        """
        Resolve references within a Pydantic model.

        Args:
            model: The Pydantic model to process

        Returns:
            The model with references resolved, or a replacement object if the
            model itself was a reference
        """
        # Check if this model has a $ref field that needs resolution
        ref_value = getattr(model, "ref", None)
        if ref_value is not None:
            resolved = self._lookup_reference(ref_value)
            if resolved is not None and resolved is not model:
                return resolved

        # Recursively process all model fields (access via class, not instance)
        for field_name in model.__class__.model_fields:
            current_value = getattr(model, field_name)
            if current_value is not None:
                resolved_value = self._resolve_recursive(current_value)
                if resolved_value is not current_value:
                    setattr(model, field_name, resolved_value)

        return model

    def _resolve_dict(self, data: dict[str, Any]) -> dict[str, Any] | Any:
        """
        Resolve references within a dictionary.

        Args:
            data: The dictionary to process

        Returns:
            The dictionary with references resolved, or a replacement object if
            the dictionary was a reference
        """
        # Check for $ref key in dictionary
        if "$ref" in data:
            ref_value = data["$ref"]
            if isinstance(ref_value, str):
                resolved = self._lookup_reference(ref_value)
                if resolved is not None:
                    return resolved

        # Recursively resolve all dictionary values
        for key, value in data.items():
            resolved_value = self._resolve_recursive(value)
            if resolved_value is not value:
                data[key] = resolved_value

        return data

    def _resolve_list(self, items: list[Any]) -> list[Any]:
        """
        Resolve references within a list.

        Args:
            items: The list to process

        Returns:
            The list with all items' references resolved
        """
        for i, item in enumerate(items):
            resolved_item = self._resolve_recursive(item)
            if resolved_item is not item:
                items[i] = resolved_item

        return items

    def _lookup_reference(self, ref: str) -> Any | None:
        """
        Look up a JSON reference pointer and return the target object.

        Args:
            ref: A JSON reference string like '#/components/schemas/User'

        Returns:
            The resolved object, or None if the reference cannot be resolved
        """
        # Only handle internal references (starting with #/)
        if not ref.startswith("#/"):
            return None

        # Parse the reference path
        path_parts = ref[2:].split("/")

        return self._navigate_path(path_parts)

    def _navigate_path(self, path_parts: list[str]) -> Any:
        """
        Navigate through the document following a path.

        Args:
            path_parts: List of path segments to follow

        Returns:
            The object at the path, or None if not found
        """
        current: Any = self._document

        for part in path_parts:
            if current is None:
                return None

            # Handle URL-encoded characters in JSON pointers
            decoded_part = part.replace("~1", "/").replace("~0", "~")

            if isinstance(current, BaseModel):
                current = getattr(current, decoded_part, None)
            elif isinstance(current, dict):
                current = cast(dict[str, Any], current).get(decoded_part)
            else:
                return None

        return current


class AsyncAPIDocument(BaseModel):
    """
    Root AsyncAPI 3.0 document containing the complete API specification.

    This model automatically resolves all $ref references to actual instances
    after validation, replacing reference objects with their targets.
    """

    asyncapi: str = "3.0.0"
    info: InfoObject
    servers: dict[str, ServerObject] | None = None
    channels: dict[str, ChannelObject]
    operations: dict[str, OperationObject] | None = None
    components: ComponentsObject | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None

    @model_validator(mode="after")
    def resolve_all_refs(self) -> AsyncAPIDocument:
        """
        Resolve all $ref pointers to actual component instances.

        This validator runs after the model is constructed and uses the
        ReferenceResolver to traverse and resolve all references.

        Returns:
            Self with all references resolved.
        """
        resolver = ReferenceResolver(self)
        resolver.resolve_all()
        return self

    def get_schema(self, name: str) -> SchemaObject | None:
        """
        Get a schema by name from components.

        Args:
            name: The name of the schema

        Returns:
            The SchemaObject if found, None otherwise
        """
        if self.components and self.components.schemas:
            return self.components.schemas.get(name)
        return None

    def get_message(self, name: str) -> MessageObject | None:
        """
        Get a message by name from components.

        Args:
            name: The name of the message

        Returns:
            The MessageObject if found, None otherwise
        """
        if self.components and self.components.messages:
            return self.components.messages.get(name)
        return None

    def get_channel(self, name: str) -> ChannelObject | None:
        """
        Get a channel by name from the channels section.

        Args:
            name: The name of the channel

        Returns:
            The ChannelObject if found, None otherwise
        """
        if self.channels:
            return self.channels.get(name)
        return None

    def get_operation(self, name: str) -> OperationObject | None:
        """
        Get an operation by name from the operations section.

        Args:
            name: The name of the operation

        Returns:
            The OperationObject if found, None otherwise
        """
        if self.operations:
            return self.operations.get(name)
        return None

    def get_server(self, name: str) -> ServerObject | None:
        """
        Get a server by name from the servers section.

        Args:
            name: The name of the server

        Returns:
            The ServerObject if found, None otherwise
        """
        if self.servers:
            return self.servers.get(name)
        return None


# -------------------------
# Ensure Pydantic resolves forward refs (safety)
# -------------------------
SchemaObject.model_rebuild()
MessageObject.model_rebuild()
OperationObject.model_rebuild()
ChannelObject.model_rebuild()
ComponentsObject.model_rebuild()
OperationReplyObject.model_rebuild()
OperationTraitObject.model_rebuild()
MessageTraitObject.model_rebuild()
ServerObject.model_rebuild()
ParameterObject.model_rebuild()
InfoObject.model_rebuild()
AsyncAPIDocument.model_rebuild()
