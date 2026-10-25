"""Tests for servers, security schemes and WebSocket bindings in the AsyncAPI spec."""

from collections.abc import MutableMapping
from typing import Any, Literal
from unittest.mock import Mock

import pytest
from chanx.asyncapi.generator import AsyncAPIGenerator
from chanx.asyncapi.type_defs import AsyncAPIDocument
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.authenticator import BaseAuthenticator, Credential
from chanx.core.decorators import channel, ws_handler
from chanx.messages.base import BaseMessage
from chanx.routing.discovery import RouteInfo
from pydantic import ValidationError


class SecureAsk(BaseMessage):
    action: Literal["secure_ask"] = "secure_ask"
    payload: str


class SecureAnswer(BaseMessage):
    action: Literal["secure_answer"] = "secure_answer"
    payload: str


class TokenAuthenticator(BaseAuthenticator):
    credentials = (
        Credential("token", "query", description="Access token"),
        Credential("Authorization", "header"),
        Credential("sessionid", "cookie"),
    )

    async def authenticate(self, scope: MutableMapping[str, Any]) -> bool:
        return True


@channel(name="secure_room")
class SecureConsumer(AsyncJsonWebsocketConsumer):
    authenticator_class = TokenAuthenticator

    @ws_handler
    async def handle_secure_ask(self, message: SecureAsk) -> SecureAnswer:
        return SecureAnswer(payload=message.payload)


ROUTE = RouteInfo(
    path="/ws/secure",
    handler=Mock(),
    base_url="ws://localhost:8000",
    consumer=SecureConsumer,
)
SCHEME_REFS = [
    {"$ref": "#/components/securitySchemes/query_token"},
    {"$ref": "#/components/securitySchemes/header_authorization"},
    {"$ref": "#/components/securitySchemes/cookie_sessionid"},
]


def test_credentials_become_schemes_bindings_and_security() -> None:
    spec = AsyncAPIGenerator([ROUTE]).generate()

    assert spec["components"]["securitySchemes"] == {
        "query_token": {
            "type": "httpApiKey",
            "name": "token",
            "in": "query",
            "description": "Access token",
        },
        "header_authorization": {
            "type": "httpApiKey",
            "name": "Authorization",
            "in": "header",
        },
        "cookie_sessionid": {"type": "httpApiKey", "name": "sessionid", "in": "cookie"},
    }
    assert spec["channels"]["secure_room"]["bindings"] == {
        "ws": {
            "query": {
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "Access token"}
                },
            },
            "headers": {
                "type": "object",
                "properties": {"Authorization": {"type": "string"}},
            },
            "bindingVersion": "0.1.0",
        }
    }
    assert spec["operations"]["handle_secure_ask"]["security"] == SCHEME_REFS


def test_camelized_refs_keep_scheme_names() -> None:
    spec = AsyncAPIGenerator([ROUTE], camelize=True).generate()
    assert spec["operations"]["handleSecureAsk"]["security"] == SCHEME_REFS
    assert set(spec["components"]["securitySchemes"]) == {
        "query_token",
        "header_authorization",
        "cookie_sessionid",
    }


def test_declared_scheme_wins_over_derived_one() -> None:
    declared = {"type": "httpApiKey", "name": "token", "in": "query", "x-note": "mine"}
    spec = AsyncAPIGenerator(
        [ROUTE], security_schemes={"query_token": declared, "oauth": {"type": "oauth2"}}
    ).generate()
    schemes = spec["components"]["securitySchemes"]
    assert schemes["query_token"] == declared
    assert schemes["oauth"] == {"type": "oauth2"}


def test_servers_replace_the_default_server() -> None:
    servers = {
        "production": {
            "host": "api.example.com",
            "protocol": "wss",
            "description": "Production",
            "security": [{"$ref": "#/components/securitySchemes/query_token"}],
        }
    }
    spec = AsyncAPIGenerator([ROUTE], servers=servers).generate()
    assert spec["servers"] == servers

    default = AsyncAPIGenerator([ROUTE]).generate()
    assert default["servers"] == {
        "development": {"host": "localhost:8000", "protocol": "ws"}
    }


def test_invalid_server_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AsyncAPIGenerator([ROUTE], servers={"bad": {"host": 1, "protocol": "wss"}})


def test_spec_round_trips_through_the_client_models() -> None:
    spec = AsyncAPIGenerator([ROUTE]).generate()
    document = AsyncAPIDocument.model_validate(spec)
    assert (
        document.channels["secure_room"].bindings
        == spec["channels"]["secure_room"]["bindings"]
    )


def test_no_credentials_adds_nothing() -> None:
    class PlainConsumer(AsyncJsonWebsocketConsumer):
        @ws_handler
        async def handle_plain_ask(self, message: SecureAsk) -> None:
            pass

    route = RouteInfo(
        path="/ws/plain", handler=Mock(), base_url="ws://x", consumer=PlainConsumer
    )
    spec = AsyncAPIGenerator([route]).generate()
    assert "securitySchemes" not in spec["components"]
    assert all("bindings" not in c for c in spec["channels"].values())
    assert all("security" not in o for o in spec["operations"].values())


def test_cookie_only_credentials_have_no_binding() -> None:
    class CookieAuthenticator(BaseAuthenticator):
        credentials = (Credential("sessionid", "cookie"),)

        async def authenticate(self, scope: MutableMapping[str, Any]) -> bool:
            return True

    class CookieConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = CookieAuthenticator

        @ws_handler
        async def handle_cookie_ask(self, message: SecureAsk) -> None:
            pass

    route = RouteInfo(
        path="/ws/cookie", handler=Mock(), base_url="ws://x", consumer=CookieConsumer
    )
    spec = AsyncAPIGenerator([route]).generate()
    assert spec["components"]["securitySchemes"] == {
        "cookie_sessionid": {"type": "httpApiKey", "name": "sessionid", "in": "cookie"}
    }
    assert all("bindings" not in c for c in spec["channels"].values())
    assert spec["operations"]["handle_cookie_ask"]["security"] == [
        {"$ref": "#/components/securitySchemes/cookie_sessionid"}
    ]
