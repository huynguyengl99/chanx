"""Functions for use in Channels routing."""

from collections.abc import Sequence
from importlib import import_module
from types import ModuleType
from typing import TypeAlias, cast

from channels.routing import URLRouter
from django.core.exceptions import ImproperlyConfigured
from django.urls import URLResolver

_URLConf: TypeAlias = str | ModuleType


def include(arg: _URLConf) -> Sequence[URLResolver]:
    """
    Include router from another module for Channels routing.

    This function can handle both:
    - Modules with a 'router' attribute that contains a list of paths
    - Modules with a 'router' attribute that is a URLRouter

    Args:
        arg: Either a string path to a module or the module itself.
             The module should have a 'router' attribute.

    Returns:
        The router from the module as a list of URLPattern.
    """
    # Check if it's a string path to module
    if isinstance(arg, str):
        imported_module = import_module(arg)
    else:
        imported_module = arg

    # Get 'router' from the module
    router = getattr(imported_module, "router", imported_module)

    # If router is already a URLRouter, return it directly
    if isinstance(router, URLRouter):
        # Cast to the correct return type
        return cast(Sequence[URLResolver], router)

    # Otherwise, make sure router is iterable
    if not isinstance(router, list | tuple):
        raise ImproperlyConfigured("'router' must be a list, tuple, or URLRouter.")

    # Return router list, ensuring it's the correct type
    return cast(Sequence[URLResolver], router)
