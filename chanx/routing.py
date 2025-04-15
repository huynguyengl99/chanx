"""Functions for use in Channels routing."""

from importlib import import_module
from types import ModuleType
from typing import TypeAlias, cast

from channels.routing import URLRouter
from django.core.exceptions import ImproperlyConfigured
from django.urls import URLPattern

_URLConf: TypeAlias = str | ModuleType


def include(arg: _URLConf) -> list[URLPattern]:
    """
    Include routes from another module for Channels routing.

    This function can handle both:
    - Modules with a 'routes' attribute that contains a list of paths
    - Modules with a 'routes' attribute that is a URLRouter

    Args:
        arg: Either a string path to a module or the module itself.
             The module should have a 'routes' attribute.

    Returns:
        The routes from the module as a list of URLPattern.
    """
    # Check if it's a string path to module
    if isinstance(arg, str):
        imported_module = import_module(arg)
    else:
        imported_module = arg

    # Get 'routes' from the module
    routes = getattr(imported_module, "routes", imported_module)

    # If routes is already a URLRouter, return it directly
    if isinstance(routes, URLRouter):
        # Cast to the correct return type
        return cast(list[URLPattern], routes)

    # Otherwise, make sure routes is iterable
    if not isinstance(routes, list | tuple):
        raise ImproperlyConfigured("'routes' must be a list, tuple, or URLRouter.")

    # Return routes list, ensuring it's the correct type
    return cast(list[URLPattern], routes)
