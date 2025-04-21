Utils Module
============

ASGI Utilities
--------------

.. module:: chanx.utils.asgi

.. autofunction:: chanx.utils.asgi.get_websocket_application

Asyncio Utilities
-----------------

.. module:: chanx.utils.asyncio

.. autofunction:: chanx.utils.asyncio.create_task

Logging Utilities
-----------------

.. module:: chanx.utils.logging

.. autodata:: chanx.utils.logging.logger
   :annotation: = structlog.get_logger("chanx")



WebSocket Utilities
-------------------

.. module:: chanx.utils.websocket

.. autoclass:: chanx.utils.websocket.RouteInfo

.. autofunction:: chanx.utils.websocket.get_websocket_routes

.. autofunction:: chanx.utils.websocket.transform_routes
