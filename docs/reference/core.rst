Core Module
===========

The core module provides the fundamental building blocks for Chanx WebSocket consumers,
including decorators, WebSocket handling, and authentication.

Decorators
----------
.. module:: chanx.core.decorators

.. autofunction:: chanx.core.decorators.channel

.. autofunction:: chanx.core.decorators.ws_handler

.. autofunction:: chanx.core.decorators.event_handler


WebSocket Consumer
------------------
.. module:: chanx.core.websocket

.. autoclass:: chanx.core.websocket.ChanxWebsocketConsumerMixin
   :members:


Authenticator
-------------
.. module:: chanx.core.authenticator

.. autoclass:: chanx.core.authenticator.BaseAuthenticator
   :members:


Configuration
-------------
.. module:: chanx.core.config

.. autoclass:: chanx.core.config.Config
   :members:


Registry
--------
.. module:: chanx.core.registry

.. autoclass:: chanx.core.registry.MessageRegistry
   :members:
