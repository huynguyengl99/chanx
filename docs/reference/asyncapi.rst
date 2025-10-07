AsyncAPI Module
===============

The AsyncAPI module provides automatic documentation generation for Chanx WebSocket consumers,
creating AsyncAPI 3.0 specifications from decorated consumers.

Generator
---------
.. module:: chanx.asyncapi.generator

.. autoclass:: chanx.asyncapi.generator.AsyncAPIGenerator
   :members:


Constants
---------
.. module:: chanx.asyncapi.constants

.. autodata:: chanx.asyncapi.constants.DEFAULT_ASYNCAPI_TITLE

.. autodata:: chanx.asyncapi.constants.DEFAULT_ASYNCAPI_VERSION

.. autodata:: chanx.asyncapi.constants.DEFAULT_SERVER_URL

.. autodata:: chanx.asyncapi.constants.DEFAULT_SERVER_PROTOCOL


Type Definitions
----------------
.. module:: chanx.asyncapi.type_defs

.. autoclass:: chanx.asyncapi.type_defs.AsyncAPIDocument
   :members:

.. autoclass:: chanx.asyncapi.type_defs.InfoObject
   :members:

.. autoclass:: chanx.asyncapi.type_defs.ServerObject
   :members:

.. autoclass:: chanx.asyncapi.type_defs.ChannelObject
   :members:

.. autoclass:: chanx.asyncapi.type_defs.OperationObject
   :members:

.. autoclass:: chanx.asyncapi.type_defs.MessageObject
   :members:

.. autoclass:: chanx.asyncapi.type_defs.SchemaObject
   :members:
