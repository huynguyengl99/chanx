Configuration
=============

Chanx Settings
--------------
Chanx can be configured through the ``CHANX`` dictionary in your Django settings. Below is a complete list of available
settings with their default values:

.. code-block:: python

    # settings.py
    CHANX = {
        # Message configuration
        'MESSAGE_ACTION_KEY': 'action',  # Key name for action field in messages
        'CAMELIZE': False,  # Whether to camelize/decamelize messages for JavaScript clients

        # Completion messages
        'SEND_COMPLETION': False,  # Whether to send completion message after processing

        # Messaging behavior
        'SEND_MESSAGE_IMMEDIATELY': True,  # Whether to yield control after sending messages (send message immediately)
        'SEND_AUTHENTICATION_MESSAGE': True,  # Whether to send auth status after connection

        # Logging configuration
        'LOG_RECEIVED_MESSAGE': True,  # Whether to log received messages
        'LOG_SENT_MESSAGE': True,  # Whether to log sent messages
        'LOG_IGNORED_ACTIONS': [],  # Message actions to ignore in logs

        # Playground configuration
        'WEBSOCKET_BASE_URL': 'ws://localhost:8000'  # Default WebSocket URL for playground
    }

Settings Reference
------------------

Message Configuration
~~~~~~~~~~~~~~~~~~~~~

- **MESSAGE_ACTION_KEY** (default: "action"): Key name for the action field in messages, used for discriminated unions.
- **CAMELIZE** (default: False): Whether to convert between camelCase (for JavaScript clients) and snake_case (for Python).

Completion Messages
~~~~~~~~~~~~~~~~~~~

- **SEND_COMPLETION** (default: False): Whether to send a completion message after processing a client message.

Messaging Behavior
~~~~~~~~~~~~~~~~~~

- **SEND_MESSAGE_IMMEDIATELY** (default: True): Whether to yield control after sending messages (send message immediately).
- **SEND_AUTHENTICATION_MESSAGE** (default: True): Whether to send authentication status after connection.

Logging Configuration
~~~~~~~~~~~~~~~~~~~~~

- **LOG_RECEIVED_MESSAGE** (default: True): Whether to log received messages.
- **LOG_SENT_MESSAGE** (default: True): Whether to log sent messages.
- **LOG_IGNORED_ACTIONS** (default: []): Message actions that should not be logged.

Playground Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

- **WEBSOCKET_BASE_URL** (default: "ws://localhost:8000"): Default WebSocket URL for playground.

Environment-Specific Settings
-----------------------------

Development
~~~~~~~~~~~

For development, you might want to use these settings:

.. code-block:: python

    # settings/dev.py
    CHANX = {
        'SEND_COMPLETION': False,
        'LOG_RECEIVED_MESSAGE': True,
        'LOG_SENT_MESSAGE': True,
        'WEBSOCKET_BASE_URL': 'ws://localhost:8000',
    }

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379/0')],
            },
        },
    }

Testing
~~~~~~~

For testing, it's recommended to use these settings:

.. code-block:: python

    # settings/test.py
    CHANX = {
        'SEND_COMPLETION': True,  # Important for receive_all_json() to work
        'SEND_AUTHENTICATION_MESSAGE': True,
        'LOG_RECEIVED_MESSAGE': False,  # Reduce noise in tests
        'LOG_SENT_MESSAGE': False,  # Reduce noise in tests
    }

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }

Production
~~~~~~~~~~

For production, consider these settings:

.. code-block:: python

    # settings/prod.py
    CHANX = {
        'SEND_COMPLETION': False,
        'SEND_MESSAGE_IMMEDIATELY': True,
        'LOG_RECEIVED_MESSAGE': True,
        'LOG_SENT_MESSAGE': True,
        'LOG_IGNORED_ACTIONS': ['ping', 'pong'],  # Reduce noise from heartbeats
        'WEBSOCKET_BASE_URL': 'wss://your-domain.com',
    }

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379/0')],
            },
        },
    }

Optional Dependencies
---------------------
Some Chanx features require additional packages. You can install these along with Chanx using extras:

.. code-block:: bash

    # Install with camelCase conversion support
    pip install chanx[camel-case]

This installs the ``pyhumps`` package which is required when using the ``CAMELIZE`` setting. Without this package
enabling the setting will raise a runtime error.

Overriding Settings in Tests
----------------------------
Chanx provides utilities for temporarily overriding settings in tests:

.. code-block:: python

    from chanx.utils.settings import override_chanx_settings

    # Using decorator for a test function
    @override_chanx_settings(SEND_COMPLETION=True)
    async def test_completion_message():
        # SEND_COMPLETION will be True within this test
        ...

Next Steps
----------
Now that you understand Chanx's configuration options, proceed to the :doc:`quick-start` guide to set up your project
and create your first WebSocket consumer.
