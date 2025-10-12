Installation
============
Requirements
------------
Chanx has the following core dependencies:

* Python 3.11+
* Pydantic 2.0+
* Structlog
* PyHumps (for camelCase conversion)
* Typing Extensions

Framework-specific dependencies are installed automatically based on which extra you choose.

Installing Chanx
----------------
**Basic Installation (Core Only)**

.. code-block:: bash

    pip install chanx

**For Django Channels Projects**

.. code-block:: bash

    pip install "chanx[channels]"

This installs:

- Django 5.0+
- Django Channels 4.0+
- Django REST Framework 3.0+
- Channels Redis 4.0+

**For FastAPI and Other ASGI Frameworks**

.. code-block:: bash

    pip install "chanx[fast_channels]"

This installs:

- FastAPI 0.117+
- fast-channels 1.0+

**Install from Source**

.. code-block:: bash

    git clone https://github.com/huynguyengl99/chanx.git
    cd chanx
    pip install -e ".[channels]"  # For Django
    # or
    pip install -e ".[fast_channels]"  # For FastAPI

Framework Setup
---------------

**Django Channels Setup**

1. Add necessary apps to your ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'rest_framework',
        'channels',
        'chanx.channels',
        # ...
    ]

2. Configure Chanx in your Django settings:

.. code-block:: python

    # settings.py
    CHANX = {
        'CAMELIZE': False,  # Set to True for camelCase conversion
        'SEND_COMPLETION': False,  # Set to True for testing
        'LOG_WEBSOCKET_MESSAGE': True,
        # ...
    }

**FastAPI Setup**

1. Create a base consumer class:

.. code-block:: python

    # base_consumer.py
    from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer

    class BaseConsumer(AsyncJsonWebsocketConsumer):
        # Configure per your needs
        send_completion = False
        log_websocket_message = True
        channel_layer_alias = "default"

2. Import and use in your consumers:

.. code-block:: python

    from chanx.core.decorators import ws_handler, channel
    from .base_consumer import BaseConsumer

    @channel(name="chat")
    class ChatConsumer(BaseConsumer):
        @ws_handler
        async def handle_ping(self, message: PingMessage) -> PongMessage:
            return PongMessage()

Configuration Options
---------------------
**camelCase Conversion**

Chanx includes automatic camelCase conversion. Enable it in your configuration:

.. code-block:: python

    # Django settings.py
    CHANX = {
        'CAMELIZE': True,
        # ...
    }

    # Or for other frameworks, in your base consumer
    class BaseConsumer(AsyncJsonWebsocketConsumer):
        camelize = True


Next Steps
----------
Now that you have Chanx installed, proceed to:

* :doc:`quick-start-django` - Create your first Django WebSocket consumer
* :doc:`quick-start-fastapi` - Create your first FastAPI WebSocket consumer
* :doc:`user-guide/prerequisites` - Start with the user guide prerequisites
* :doc:`examples/django` - See Django implementation examples
* :doc:`examples/fastapi` - See FastAPI implementation examples
