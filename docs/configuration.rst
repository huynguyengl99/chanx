Configuration
=============

General Configuration (All Frameworks)
---------------------------------------

Chanx can be configured by creating a base consumer class and setting class attributes. This approach works across all frameworks (Django, FastAPI, and other ASGI frameworks).

**Creating a Base Consumer**

.. code-block:: python

    from chanx.core.websocket import AsyncJsonWebsocketConsumer

    class BaseConsumer(AsyncJsonWebsocketConsumer):
        # Message behavior
        send_completion = False  # Whether to send completion message after processing
        send_message_immediately = True  # Whether to yield control after sending messages
        log_websocket_message = True  # Whether to log websocket messages
        log_ignored_actions = []  # Message actions to ignore in logs

        # Message formatting
        camelize = False  # Whether to convert between camelCase and snake_case
        discriminator_field = "action"  # Field used for message type discrimination

        # Channel layer configuration (required for non-Django frameworks)
        channel_layer_alias = "default"  # Channel layer alias to use

        # Authentication (optional)
        # authenticator_class = MyAuthenticator  # Set authenticator class
        # authenticator: MyAuthenticator  # Type hint for authenticator

**Using Your Base Consumer**

.. code-block:: python

    from chanx.core.decorators import ws_handler, channel
    from .base_consumer import BaseConsumer

    @channel(name="chat")
    class ChatConsumer(BaseConsumer):
        # Override settings for this specific consumer if needed
        send_completion = True
        log_ignored_actions = ["ping", "pong"]

        @ws_handler
        async def handle_chat(self, message: ChatMessage) -> None:
            await self.broadcast_message(...)

**Authentication Configuration**

.. code-block:: python

    from chanx.channels.authenticator import DjangoAuthenticator
    from rest_framework.permissions import IsAuthenticated

    class MyAuthenticator(DjangoAuthenticator):
        permission_classes = [IsAuthenticated]
        queryset = MyModel.objects.all()
        obj: MyModel  # Type hint for the authenticated object

    class MyConsumer(BaseConsumer):
        authenticator_class = MyAuthenticator
        authenticator: MyAuthenticator  # Type hint for better IDE support

Configurable Attributes Reference
----------------------------------

**Message Behavior**

- **send_completion** (bool): Whether to send completion message after processing (default: False)
- **send_message_immediately** (bool | None): Whether to yield control after sending messages (default: True)
- **log_websocket_message** (bool | None): Whether to log websocket messages (default: True)
- **log_ignored_actions** (Collection[str]): Message actions to ignore in logs (default: [])

**Message Formatting**

- **camelize** (ClassVar[bool]): Whether to convert between camelCase and snake_case (default: False)
- **discriminator_field** (ClassVar[str]): Field used for message type discrimination (default: "action")

**Channel Layer**

- **channel_layer_alias** (ClassVar[str]): Channel layer alias to use. **Required for non-Django frameworks**. For Django, you can skip this and it will use default, or specify to use the right channel layer.

**Authentication**

- **authenticator_class** (type[BaseAuthenticator] | None): Authenticator class to instantiate (default: None)
- **authenticator** (BaseAuthenticator | None): Type hint for the active authenticator instance

Django-Specific Configuration
------------------------------

For Django projects, you can use the ``CHANX`` settings dictionary in addition to or instead of creating a base consumer class. **Note: CHANX settings apply to Django only.**

.. code-block:: python

    # settings.py
    CHANX = {
        # Message configuration
        'MESSAGE_ACTION_KEY': 'action',  # Field used for message type discrimination
        'CAMELIZE': False,  # Whether to convert between camelCase and snake_case

        # Completion messages
        'SEND_COMPLETION': False,  # Whether to send completion message after processing

        # Messaging behavior
        'SEND_MESSAGE_IMMEDIATELY': True,  # Whether to yield control after sending messages
        'LOG_WEBSOCKET_MESSAGE': True,  # Whether to log websocket messages
        'LOG_IGNORED_ACTIONS': [],  # Message actions to ignore in logs

        # AsyncAPI documentation settings
        'ASYNCAPI_TITLE': 'AsyncAPI Documentation',
        'ASYNCAPI_DESCRIPTION': '',
        'ASYNCAPI_VERSION': '1.0.0',
        'ASYNCAPI_SERVER_URL': None,
        'ASYNCAPI_SERVER_PROTOCOL': None,
    }

**Using Django Settings**

You can use CHANX settings for some attributes instead of creating a base consumer:

.. code-block:: python

    from chanx.core.websocket import AsyncJsonWebsocketConsumer

    class MyConsumer(AsyncJsonWebsocketConsumer):
        # These will use CHANX settings automatically
        # send_completion, camelize, etc. read from settings

        # You can still override specific settings
        log_ignored_actions = ["ping", "pong"]

        # Django automatically sets channel_layer_alias
        # authenticator_class = MyAuthenticator  # Set if needed

Environment-Specific Configuration Examples
--------------------------------------------

**Testing Configuration**

For testing, it's recommended to enable completion messages:

.. code-block:: python

    # Django settings/test.py
    CHANX = {
        'SEND_COMPLETION': True,  # Important for receive_all_messages() to work
        'LOG_WEBSOCKET_MESSAGE': False,  # Reduce noise in tests
        'LOG_IGNORED_ACTIONS': [],
    }

    # Or for other frameworks, in base consumer
    class BaseConsumer(AsyncJsonWebsocketConsumer):
        send_completion = True  # Enable for testing
        log_websocket_message = False  # Reduce test noise

**Production Configuration**

For production, consider performance and logging:

.. code-block:: python

    # Django settings/prod.py
    CHANX = {
        'SEND_COMPLETION': False,
        'LOG_WEBSOCKET_MESSAGE': True,
        'LOG_IGNORED_ACTIONS': ['ping', 'pong'],  # Reduce noise from heartbeats
    }

    # Or for other frameworks
    class BaseConsumer(AsyncJsonWebsocketConsumer):
        send_completion = False
        log_websocket_message = True
        log_ignored_actions = ['ping', 'pong']

**Framework-Specific Examples**

.. code-block:: python

    # FastAPI example
    import os
    from chanx.core.websocket import AsyncJsonWebsocketConsumer

    class BaseConsumer(AsyncJsonWebsocketConsumer):
        send_completion = bool(os.environ.get("SEND_COMPLETION", False))
        channel_layer_alias = "default"  # Required for non-Django

    # Django example - no channel_layer_alias needed
    class DjangoConsumer(AsyncJsonWebsocketConsumer):
        # Uses CHANX settings automatically
        authenticator_class = MyDjangoAuthenticator

Next Steps
----------
Now that you understand Chanx's configuration options, proceed to the framework-specific quick-start guides:

* :doc:`quick-start-django` - Set up your Django project and create your first WebSocket consumer
* :doc:`quick-start-fastapi` - Set up your FastAPI project and create your first WebSocket consumer
