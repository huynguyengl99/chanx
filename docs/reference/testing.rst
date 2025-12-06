Testing
=======

The testing modules provide specialized testing utilities for WebSocket consumers, including enhanced
communicators and base test case classes with authentication support and message collection capabilities.


Core Testing
------------

.. module:: chanx.core.testing

The core testing module provides the foundation for Chanx's testing infrastructure with a framework-agnostic mixin.

.. autoclass:: chanx.core.testing.WebsocketCommunicatorMixin
   :members:
   :undoc-members:

.. autoclass:: chanx.core.testing.CapturedBroadcastEvent
   :members:
   :undoc-members:

.. autofunction:: chanx.core.testing.capture_broadcast_events


Django Channels Testing
-----------------------

.. module:: chanx.channels.testing

The Django Channels testing module provides Django-specific testing utilities.

.. autoclass:: chanx.channels.testing.WebsocketCommunicator
   :members:
   :undoc-members:

.. autoclass:: chanx.channels.testing.DjangoWebsocketCommunicator
   :members:
   :undoc-members:

.. autoclass:: chanx.channels.testing.WebsocketTestCase
   :members:
   :undoc-members:


FastAPI Testing
---------------

.. module:: chanx.fast_channels.testing

The FastAPI testing module provides FastAPI-specific testing utilities.

.. autoclass:: chanx.fast_channels.testing.WebsocketCommunicator
   :members:
   :undoc-members:
