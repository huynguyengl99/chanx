Extensions
==========

Chanx provides framework-specific extensions for Django Channels and FastAPI.

Django Channels Extension
-------------------------

The Channels extension provides seamless integration with Django Channels,
including views for AsyncAPI documentation and testing utilities.

.. module:: chanx.ext.channels

Views
~~~~~
.. module:: chanx.ext.channels.views

.. autoclass:: chanx.ext.channels.views.AsyncAPISchemaView
   :members:

.. autoclass:: chanx.ext.channels.views.AsyncAPIDocsView
   :members:

.. autofunction:: chanx.ext.channels.views.generate_asyncapi_schema


Authenticator
~~~~~~~~~~~~~
.. module:: chanx.ext.channels.authenticator

Django REST Framework integration for WebSocket authentication.

.. autoclass:: chanx.ext.channels.authenticator.DjangoAuthenticator
   :members:
   :exclude-members: authenticate

   .. automethod:: authenticate(scope: dict[str, Any]) -> bool
      :async:

.. autoclass:: chanx.ext.channels.authenticator.ChanxAuthView
   :members:


Testing
~~~~~~~
.. module:: chanx.ext.channels.testing

.. autoclass:: chanx.ext.channels.testing.DjangoWebsocketCommunicator
   :members:

.. autoclass:: chanx.ext.channels.testing.WebsocketTestCase
   :members:


Utils
~~~~~
.. module:: chanx.ext.channels.utils.asgi

.. autofunction:: chanx.ext.channels.utils.asgi.get_websocket_application


Settings
~~~~~~~~
.. module:: chanx.ext.channels.settings

The Django Channels extension provides configuration through Django's settings system.
All Chanx settings are contained within a single ``CHANX`` dictionary in your project's settings file.

Configuration Options
^^^^^^^^^^^^^^^^^^^^^^
Here's an overview of all available settings and their default values:

.. code-block:: python

    # settings.py
    CHANX = {
        'MESSAGE_ACTION_KEY': 'action',
        'SEND_COMPLETION': False,
        'SEND_MESSAGE_IMMEDIATELY': True,
        'SEND_AUTHENTICATION_MESSAGE': True,
        'CAMELIZE': False,
        'LOG_WEBSOCKET_MESSAGE': True,
        'LOG_IGNORED_ACTIONS': ['ping', 'pong'],
        'WEBSOCKET_BASE_URL': None,
        # AsyncAPI documentation settings
        'ASYNCAPI_TITLE': 'AsyncAPI Documentation',
        'ASYNCAPI_DESCRIPTION': '',
        'ASYNCAPI_VERSION': '1.0.0',
        'ASYNCAPI_SERVER_URL': None,
        'ASYNCAPI_SERVER_PROTOCOL': None,
    }

Settings Details
^^^^^^^^^^^^^^^^
.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Setting
     - Default
     - Description
   * - ``MESSAGE_ACTION_KEY``
     - ``"action"``
     - Key name for the action field in messages, used as the discriminator for message types
   * - ``SEND_COMPLETION``
     - ``False``
     - Whether to send completion messages after processing a client message, should set it to `True` for testing and `False` for the other environments.
   * - ``SEND_MESSAGE_IMMEDIATELY``
     - ``True``
     - Whether to send message immediately rather than wait to the end of the processing to send together.
   * - ``SEND_AUTHENTICATION_MESSAGE``
     - ``True``
     - Whether to send authentication status message after connection authentication
   * - ``CAMELIZE``
     - ``False``
     - Whether to convert message keys to camelCase format using pyhumps. When enabled, requires either installing Chanx with the ``camel-case`` extra (``pip install chanx[camel-case]``) or manually installing the pyhumps package (``pip install pyhumps``).
   * - ``LOG_WEBSOCKET_MESSAGE``
     - ``True``
     - Whether to log WebSocket messages (both received and sent)
   * - ``LOG_IGNORED_ACTIONS``
     - ``[]``
     - List of message actions that should not be logged (e.g., frequent messages like heartbeats)
   * - ``WEBSOCKET_BASE_URL``
     - ``None``
     - WebSocket URL for overriding in development or testing
   * - ``ASYNCAPI_TITLE``
     - ``"AsyncAPI Documentation"``
     - Title for generated AsyncAPI documentation
   * - ``ASYNCAPI_DESCRIPTION``
     - ``""``
     - Description for generated AsyncAPI documentation
   * - ``ASYNCAPI_VERSION``
     - ``"1.0.0"``
     - Version for generated AsyncAPI documentation
   * - ``ASYNCAPI_SERVER_URL``
     - ``None``
     - Server URL for AsyncAPI documentation (auto-detected if not set)
   * - ``ASYNCAPI_SERVER_PROTOCOL``
     - ``None``
     - Server protocol for AsyncAPI documentation (auto-detected if not set)

Using Settings in Code
^^^^^^^^^^^^^^^^^^^^^^^
Chanx's settings are accessible through the ``chanx_settings`` object:

.. code-block:: python

    from chanx.ext.channels.settings import chanx_settings

    # Access a setting
    action_key = chanx_settings.MESSAGE_ACTION_KEY

    # Check if completion messages are enabled
    if chanx_settings.SEND_COMPLETION:
        # Do something

Optional Dependencies
^^^^^^^^^^^^^^^^^^^^^
Some Chanx features require additional packages. You can install these along with Chanx using extras:

.. code-block:: bash

    # Install with camelCase conversion support
    pip install chanx[camel-case]

This installs the ``pyhumps`` package which is required when using the ``CAMELIZE`` setting. Without this package
enabling the setting will raise a runtime error.


FastAPI Extension
-----------------

The FastAPI extension provides integration utilities for FastAPI applications.

.. module:: chanx.ext.fast_channels

Views
~~~~~
.. module:: chanx.ext.fast_channels.views

.. autofunction:: chanx.ext.fast_channels.views.asyncapi_docs

.. autofunction:: chanx.ext.fast_channels.views.asyncapi_spec_json

.. autofunction:: chanx.ext.fast_channels.views.asyncapi_spec_yaml
