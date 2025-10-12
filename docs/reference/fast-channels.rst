FastAPI & ASGI Frameworks Integration
======================================

Chanx provides integration for FastAPI and other ASGI-based frameworks through the fast-channels module,
including WebSocket consumers, AsyncAPI documentation views, and testing utilities. Works with any ASGI framework
including FastAPI, Starlette, Litestar, and more.

.. module:: chanx.fast_channels

WebSocket Consumer
------------------
.. module:: chanx.fast_channels.websocket

.. autoclass:: chanx.fast_channels.websocket.AsyncJsonWebsocketConsumer
   :members:


Views
-----
.. module:: chanx.fast_channels.views

.. autofunction:: chanx.fast_channels.views.asyncapi_docs

.. autofunction:: chanx.fast_channels.views.asyncapi_spec_json

.. autofunction:: chanx.fast_channels.views.asyncapi_spec_yaml


Testing
-------
.. module:: chanx.fast_channels.testing

.. autoclass:: chanx.fast_channels.testing.WebsocketCommunicator
   :members:


Configuration
-------------

For ASGI-based frameworks, configuration is done via class attributes on your consumer:

.. code-block:: python

    from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer

    class BaseConsumer(AsyncJsonWebsocketConsumer):
        # Message handling
        camelize = False
        discriminator_field = "action"
        send_completion = False
        send_message_immediately = True

        # Logging
        log_websocket_message = False
        log_ignored_actions = []

        # Channel layer
        channel_layer_alias = "default"

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Attribute
     - Default
     - Description
   * - ``discriminator_field``
     - ``"action"``
     - Key name for the action field in messages, used as the discriminator for message types
   * - ``send_completion``
     - ``False``
     - Whether to send completion messages after processing a client message
   * - ``send_message_immediately``
     - ``True``
     - Whether to send message immediately rather than wait to the end of processing
   * - ``camelize``
     - ``False``
     - Whether to convert message keys to camelCase format using pyhumps
   * - ``log_websocket_message``
     - ``False``
     - Whether to log WebSocket messages (both received and sent)
   * - ``log_ignored_actions``
     - ``[]``
     - List of message actions that should not be logged
   * - ``channel_layer_alias``
     - ``"default"``
     - Channel layer alias to use for broadcasting and events
