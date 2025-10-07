"""
AsyncAPI 3.0 data models for specification generation.

This module contains Pydantic models representing all AsyncAPI 3.0 specification
objects including schemas, messages, operations, channels, and the root document.
These models are used to generate valid AsyncAPI documentation from Chanx WebSocket
consumers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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

    # AsyncAPI allows different ways to express address; include common fields
    url: str | None = None
    host: str | None = None
    protocol: str | None = None
    protocolVersion: str | None = None
    pathname: str | None = None
    description: str | None = None
    title: str | None = None
    summary: str | None = None
    # e.g. [{"oauth2": ["scope1"]}]
    security: list[dict[str, list[str]]] | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    # protocol-specific server bindings (kept generic)
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

    # support $ref alias for message references
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
    # channel may be a $ref pointer or inline channel object
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

    action: str | None = None  # "send" | "receive"
    # channel may be $ref or inline
    channel: dict[str, Any] | None = None
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    security: list[dict[str, list[str]]] | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None
    bindings: dict[str, dict[str, Any]] | None = None
    # traits may be inline or $ref (dict)
    traits: list[OperationTraitObject | dict[str, Any]] | None = None
    # messages may be list of MessageObject or $ref dicts
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

    # channel address, e.g. 'users.{userId}'
    address: str | None = None
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    # servers may be $ref pointers like ["#/servers/production"]
    servers: list[str] | None = None
    parameters: dict[str, ParameterObject] | None = None
    # messages map name -> MessageObject or $ref-dict
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


class AsyncAPIDocument(BaseModel):
    """Root AsyncAPI 3.0 document containing the complete API specification."""

    asyncapi: str = "3.0.0"
    info: InfoObject
    servers: dict[str, ServerObject] | None = None
    channels: dict[str, ChannelObject] | None = None
    operations: dict[str, OperationObject] | None = None
    components: ComponentsObject | None = None
    tags: list[TagObject] | None = None
    externalDocs: ExternalDocumentationObject | None = None


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
