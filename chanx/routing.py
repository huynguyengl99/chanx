"""
URL routing utilities for Django Channels applications.
This module provides functions to simplify routing configuration in Django Channels projects.
It extends Django Channels' routing capabilities with improved include functionality for
modular routing organization.
Functions:
include: Includes URL patterns from another module, similar to Django's include function
but specifically designed for Channels routing.
"""

from importlib import import_module
from types import ModuleType
from typing import TypeAlias

from channels.routing import URLRouter

_URLConf: TypeAlias = URLRouter | str | ModuleType


def include(arg: _URLConf) -> URLRouter:
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
    if isinstance(arg, URLRouter):
        router = arg
    else:
        if isinstance(arg, str):
            imported_module = import_module(arg)
        else:
            imported_module = arg
        # Get 'router' from the module
        router = imported_module.router

    # If router is already a URLRouter, return it directly

    # Return router list, ensuring it's the correct type
    return router
