"""Tests for chanx.routing functions."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

from channels.routing import URLRouter
from django.core.exceptions import ImproperlyConfigured
from django.urls import path

import pytest
from chanx.routing import include


class TestIncludeFunction:
    """Test class for the include function in chanx.routing."""

    def setup_method(self):
        """Set up test data before each test method."""
        # Set up a mock consumer for creating test patterns
        self.consumer = MagicMock()

        # Set up chat.routing-like module for testing
        self.chat_module = ModuleType("chat.routing")
        self.chat_module.router = URLRouter(
            [
                path("", self.consumer, name="chat_consumer"),
            ]
        )

        # Module with router as a list
        self.list_module = ModuleType("list_module")
        self.list_module.router = [
            path("test1/", self.consumer, name="test1"),
            path("test2/", self.consumer, name="test2"),
        ]

        # Module without a router attribute
        self.no_router_module = ModuleType("no_router_module")

        # Keep reference to sys.modules to restore later
        self.original_modules = dict(sys.modules)

        # Add our test modules to sys.modules
        sys.modules["chat.routing"] = self.chat_module
        sys.modules["list_module"] = self.list_module
        sys.modules["no_router_module"] = self.no_router_module

    def teardown_method(self):
        """Clean up after each test method."""
        # Restore original sys.modules
        sys.modules.clear()
        sys.modules.update(self.original_modules)

    def test_include_with_real_module_string(self):
        """Test include with a string path to a module with URLRouter."""
        # This should work with the real module import
        result = include("chat.routing")
        assert isinstance(result, URLRouter)
        assert len(result.routes) == 1
        assert result.routes[0].name == "chat_consumer"

    def test_include_with_list_router_module(self):
        """Test include with a module that has a router attribute as a list."""
        result = include("list_module")
        assert len(result) == 2
        assert result[0].name == "test1"
        assert result[1].name == "test2"

    def test_include_with_module_object(self):
        """Test include with a direct module object rather than string."""
        result = include(self.chat_module)
        assert isinstance(result, URLRouter)

    def test_include_with_no_router_module(self):
        """Test include with a module that lacks a router attribute."""
        with pytest.raises(ImproperlyConfigured):
            include("no_router_module")

    def test_include_with_invalid_router_type(self):
        """Test include with a module that has an invalid router type."""
        # Create a module with a router that's not a list, tuple, or URLRouter
        invalid_module = ModuleType("invalid_module")
        invalid_module.router = "not a valid router"
        sys.modules["invalid_module"] = invalid_module

        with pytest.raises(ImproperlyConfigured):
            include("invalid_module")

    def test_include_with_tuple_router(self):
        """Test include with a module that has a router attribute as a tuple."""
        # Create a module with a router that's a tuple
        tuple_module = ModuleType("tuple_module")
        tuple_module.router = [
            path("tuple1/", self.consumer, name="tuple1"),
            path("tuple2/", self.consumer, name="tuple2"),
        ]
        sys.modules["tuple_module"] = tuple_module

        result = include("tuple_module")
        assert len(result) == 2
        assert result[0].name == "tuple1"
