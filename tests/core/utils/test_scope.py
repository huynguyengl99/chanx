"""Tests for portable ASGI scope access."""

from typing import Any

import pytest
from chanx.utils.scope import path_param, path_params, query_params, scope_user


class TestPathParams:
    def test_reads_channels_url_route(self) -> None:
        scope: dict[str, Any] = {"url_route": {"kwargs": {"pk": "5"}}}

        assert path_params(scope) == {"pk": "5"}

    def test_reads_starlette_path_params(self) -> None:
        scope: dict[str, Any] = {"path_params": {"room": "lobby"}}

        assert path_params(scope) == {"room": "lobby"}

    def test_empty_when_neither_framework_populated_them(self) -> None:
        assert path_params({}) == {}

    def test_url_route_without_kwargs_falls_through(self) -> None:
        scope: dict[str, Any] = {"url_route": {}, "path_params": {"pk": "7"}}

        assert path_params(scope) == {"pk": "7"}


class TestPathParam:
    def test_returns_the_capture(self) -> None:
        assert path_param({"path_params": {"pk": "5"}}, "pk") == "5"

    def test_missing_capture_raises(self) -> None:
        with pytest.raises(KeyError, match="No path parameter 'pk'"):
            path_param({}, "pk")

    def test_missing_capture_with_default(self) -> None:
        assert path_param({}, "pk", default=None) is None


class TestQueryParams:
    def test_parses_bytes(self) -> None:
        scope: dict[str, Any] = {"query_string": b"as=ana&tag=a&tag=b"}

        assert query_params(scope) == {"as": ["ana"], "tag": ["a", "b"]}

    def test_accepts_str_and_absent(self) -> None:
        assert query_params({"query_string": "as=bo"}) == {"as": ["bo"]}
        assert query_params({}) == {}


class TestScopeUser:
    def test_authenticated_user_is_returned(self) -> None:
        class User:
            is_authenticated = True

        user = User()
        assert scope_user({"user": user}) is user

    def test_anonymous_user_is_none(self) -> None:
        class Anonymous:
            is_authenticated = False

        assert scope_user({"user": Anonymous()}) is None

    def test_absent_user_is_none(self) -> None:
        assert scope_user({}) is None

    def test_user_without_the_flag_counts_as_authenticated(self) -> None:
        class Plain:
            pass

        user = Plain()
        assert scope_user({"user": user}) is user
