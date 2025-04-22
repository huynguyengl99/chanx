Settings Reference
==================
Chanx can be configured through Django's settings module. All Chanx settings are contained within a single ``CHANX`` dictionary in your project's settings file.

Configuration Options
---------------------
Here's an overview of all available settings and their default values:

.. code-block:: python

    # settings.py
    CHANX = {
        'MESSAGE_ACTION_KEY': 'action',
        'SEND_COMPLETION': False,
        'SEND_MESSAGE_IMMEDIATELY': True,
        'SEND_AUTHENTICATION_MESSAGE': True,
        'CAMELIZE': False,
        'LOG_RECEIVED_MESSAGE': True,
        'LOG_SENT_MESSAGE': True,
        'LOG_IGNORED_ACTIONS': ['ping', 'pong'],
        'WEBSOCKET_BASE_URL': 'ws://localhost:8000',
    }

Settings Details
----------------
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
     - Whether to convert message keys to camelCase format using pyhumps. Requires the pyhumps package to be installed.
   * - ``LOG_RECEIVED_MESSAGE``
     - ``True``
     - Whether to log received WebSocket messages
   * - ``LOG_SENT_MESSAGE``
     - ``True``
     - Whether to log sent WebSocket messages
   * - ``LOG_IGNORED_ACTIONS``
     - ``[]``
     - List of message actions that should not be logged (e.g., frequent messages like heartbeats)
   * - ``WEBSOCKET_BASE_URL``
     - ``"ws://localhost:8000"``
     - Default WebSocket URL for discovery and playground usage

Using Settings in Code
----------------------
Chanx's settings are accessible through the ``chanx_settings`` object:

.. code-block:: python

    from chanx.settings import chanx_settings

    # Access a setting
    action_key = chanx_settings.MESSAGE_ACTION_KEY

    # Check if completion messages are enabled
    if chanx_settings.SEND_COMPLETION:
        # Do something

Overriding Settings in Tests
----------------------------
Chanx provides utilities for temporarily overriding settings in tests:

.. code-block:: python

    from chanx.utils.settings import override_chanx_settings, settings_context

    # Using decorator for a test function
    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_completion_message():
        # SEND_COMPLETION will be True within this test
        ...

    # Using context manager
    async def test_with_custom_settings():
        with settings_context(SEND_AUTHENTICATION_MESSAGE=False):
            # SEND_AUTHENTICATION_MESSAGE will be False within this block
            ...

Default Settings Source
-----------------------
The default settings are defined in ``chanx.settings.MySetting`` as a dataclass:

.. literalinclude:: ../../chanx/settings.py
   :language: python
   :pyobject: MySetting
   :linenos:
