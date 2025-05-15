"""Tests for chanx.routing functions."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

from channels.routing import URLRouter
from django.urls import URLPattern

import pytest
from chanx.routing import include, path


class TestIncludeFunction:
    """Test class for the include function in chanx.routing."""

    def setup_method(self) -> None:
        """Set up test data before each test method."""
        # Set up a mock consumer for creating test patterns
        self.consumer = MagicMock()

        # Set up chat.routing-like module for testing
        self.chat_module = ModuleType("chat.routing")
        self.chat_module.router = URLRouter(  # type: ignore[attr-defined]
            [
                path("", self.consumer, name="chat_consumer"),
                path("test2/", self.consumer, name="test2"),
            ]
        )

        # Module without a router attribute
        self.no_router_module = ModuleType("no_router_module")

        # Keep reference to sys.modules to restore later
        self.original_modules = dict(sys.modules)

        # Add our test modules to sys.modules
        sys.modules["chat.routing"] = self.chat_module
        sys.modules["no_router_module"] = self.no_router_module

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # Restore original sys.modules
        sys.modules.clear()
        sys.modules.update(self.original_modules)

    def test_include_with_real_module_string(self) -> None:
        """Test include with a string path to a module with URLRouter."""
        # This should work with the real module import
        result = include("chat.routing")
        assert isinstance(result, URLRouter)
        assert len(result.routes) == 2
        first_route = result.routes[0]
        assert isinstance(first_route, URLPattern)
        assert first_route.name == "chat_consumer"

        second_route = result.routes[1]
        assert isinstance(second_route, URLPattern)
        assert second_route.name == "test2"

    def test_include_with_module_object(self) -> None:
        """Test include with a direct module object rather than string."""
        result = include(self.chat_module)
        assert isinstance(result, URLRouter)

    def test_include_with_no_router_module(self) -> None:
        """Test include with a module that lacks a router attribute."""
        with pytest.raises(AttributeError):
            include("no_router_module")
