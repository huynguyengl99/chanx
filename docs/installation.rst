Installation
============
Requirements
------------
Chanx has the following dependencies:

* Python 3.10+
* Django 4.0+
* Django Channels 4.0+
* Django REST Framework 3.13+
* Pydantic 2.0+
* Structlog 23.0+

Installing Chanx
----------------
You can install Chanx from PyPI:

.. code-block:: bash

    pip install chanx

Or install from source:

.. code-block:: bash

    git clone https://github.com/username/chanx.git
    cd chanx
    pip install -e .

Configuration
-------------
1. Add Chanx to your ``INSTALLED_APPS`` in Django settings:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'rest_framework',
        'channels',
        'chanx',
        # ...
    ]

2. Make sure Django Channels is properly configured:

.. code-block:: python

    # settings.py
    ASGI_APPLICATION = "myproject.asgi.application"

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("127.0.0.1", 6379)],
            },
        },
    }

3. Configure Chanx settings (optional):

.. code-block:: python

    # settings.py
    CHANX = {
        'SEND_COMPLETION': True,
        'SEND_AUTHENTICATION_MESSAGE': True,
        'LOG_RECEIVED_MESSAGE': True,
        'LOG_SENT_MESSAGE': True,
        'LOG_IGNORED_ACTIONS': ['ping', 'pong'],
        'WEBSOCKET_BASE_URL': 'ws://localhost:8000',
    }

4. Set up your ASGI application with a WebSocket router:

.. code-block:: python

    # asgi.py
    import os
    from django.core.asgi import get_asgi_application
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack

    from myapp.routing import websocket_urlpatterns

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

    application = ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

5. Create your WebSocket URL patterns:

.. code-block:: python

    # myapp/routing.py
    from django.urls import re_path
    from myapp.consumers import MyConsumer

    websocket_urlpatterns = [
        re_path(r'ws/myendpoint/$', MyConsumer.as_asgi()),
    ]

6. (Optional) Set up the WebSocket playground:

.. code-block:: python

    # myproject/urls.py
    from django.urls import path, include

    urlpatterns = [
        # ...
        path('chanx/', include('chanx.playground.urls')),
        # ...
    ]

Verifying Installation
----------------------
To verify that Chanx is correctly installed and configured:

1. Start your Django development server:

.. code-block:: bash

    python manage.py runserver

2. If you've set up the playground, navigate to:

   http://localhost:8000/chanx/playground/websocket/

   You should see the WebSocket playground interface where you can explore your WebSocket endpoints.

3. Access the WebSocket endpoint with a client like wscat:

.. code-block:: bash

    wscat -c ws://localhost:8000/ws/myendpoint/

Troubleshooting
---------------
**Can't connect to WebSocket endpoint**

* Ensure your ASGI server is running
* Check your URL patterns in routing.py
* Verify your ProtocolTypeRouter setup
* Check authentication requirements

**Authentication issues**

* Verify your authentication classes are properly configured
* Check that your WebSocket request includes necessary headers
* Inspect the WebSocket authentication message response

**Django server won't start**

* Look for import errors related to Chanx dependencies
* Verify your ASGI_APPLICATION setting is correct
* Check for exceptions during application startup

Next Steps
----------
Now that you have Chanx installed and configured, proceed to the :doc:`quick-start` guide to create your first WebSocket consumer.
