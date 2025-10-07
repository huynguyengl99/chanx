Routing
=======

The routing module provides utilities for organizing WebSocket routes and patterns,
including route discovery and traversal.

Patterns
--------
.. module:: chanx.routing.patterns

.. autofunction:: chanx.routing.patterns.get_pattern_string_and_params

.. autofunction:: chanx.routing.patterns.extract_path_parameters

.. autodata:: chanx.routing.patterns.DJANGO_PARAM_PATTERN

.. autodata:: chanx.routing.patterns.REGEX_PARAM_PATTERN

.. autodata:: chanx.routing.patterns.STARLETTE_PARAM_PATTERN


Discovery
---------
.. module:: chanx.routing.discovery

.. autoclass:: chanx.routing.discovery.RouteInfo
   :members:

.. autoclass:: chanx.routing.discovery.RouteDiscovery
   :members:


Traversal
---------
.. module:: chanx.routing.traversal

.. autofunction:: chanx.routing.traversal.traverse_middleware_stack
