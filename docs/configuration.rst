Configuration
=============

Chanx Settings
-------------
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
-----------------

Message Configuration
~~~~~~~~~~~~~~~~~~~~

- **MESSAGE_ACTION_KEY** (default: "action"): Key name for the action field in messages, used for discriminated unions.
- **CAMELIZE** (default: False): Whether to convert between camelCase (for JavaScript clients) and snake_case (for Python).

Completion Messages
~~~~~~~~~~~~~~~~~

- **SEND_COMPLETION** (default: False): Whether to send a completion message after processing a client message.

Messaging Behavior
~~~~~~~~~~~~~~~~

- **SEND_MESSAGE_IMMEDIATELY** (default: True): Whether to yield control after sending messages (send message immediately).
- **SEND_AUTHENTICATION_MESSAGE** (default: True): Whether to send authentication status after connection.

Logging Configuration
~~~~~~~~~~~~~~~~~~~

- **LOG_RECEIVED_MESSAGE** (default: True): Whether to log received messages.
- **LOG_SENT_MESSAGE** (default: True): Whether to log sent messages.
- **LOG_IGNORED_ACTIONS** (default: []): Message actions that should not be logged.

Playground Configuration
~~~~~~~~~~~~~~~~~~~~~~

- **WEBSOCKET_BASE_URL** (default: "ws://localhost:8000"): Default WebSocket URL for playground.

Next Steps
---------
Now that you understand Chanx's configuration options, proceed to the :doc:`quick-start` guide to set up your project
and create your first WebSocket consumer.
