Installation
============
Requirements
------------
Chanx has the following dependencies:

* Python 3.10+
* Django 5.0+
* Django Channels 4.0+
* Django REST Framework 3+
* Pydantic 2.0+
* Structlog 23.1+

Installing Chanx
----------------
You can install Chanx from PyPI:

.. code-block:: bash

    pip install chanx

For installations with additional features:

.. code-block:: bash

    # Install with camelCase conversion support
    pip install chanx[camel-case]

Or install from source:

.. code-block:: bash

    git clone https://github.com/huynguyengl99/chanx.git
    cd chanx
    pip install -e .

    # Or with extras
    pip install -e ".[camel-case]"

Basic Setup
-----------
1. Add necessary apps to your ``INSTALLED_APPS`` in Django settings:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'rest_framework',
        'channels',
        'chanx.playground',  # Only needed for the WebSocket playground
        # ...
    ]

.. note::
  The ``chanx.playground`` app provides an interactive WebSocket testing interface.
  It's highly recommended for development as it allows you to explore and test
  your WebSocket endpoints without writing client-side code.

2. Set up the WebSocket playground URLs:

.. code-block:: python

    # urls.py
    from django.urls import path, include

    urlpatterns = [
        # ...
        path('playground/', include('chanx.playground.urls')),
        # ...
    ]

Optional Features
----------------
Chanx offers additional features through optional dependencies:

**camelCase Conversion**

If you want to automatically convert message keys between snake_case (Python) and camelCase (JavaScript),
you need to install the pyhumps package:

.. code-block:: bash

    pip install chanx[camel-case]

Then enable the feature in your settings:

.. code-block:: python

    # settings.py
    CHANX = {
        'CAMELIZE': True,
        # Other settings...
    }

This will automatically convert snake_case fields to camelCase when sending to clients
and convert camelCase back to snake_case when receiving from clients.

Verifying Installation
----------------------
To verify that Chanx is correctly installed:

1. Start your Django development server:

.. code-block:: bash

    python manage.py runserver

2. Navigate to the playground:

   http://localhost:8000/playground/websocket/

   You should see the WebSocket playground interface.

Next Steps
----------
Now that you have Chanx installed, proceed to:

* :doc:`configuration` - Configure Chanx settings
* :doc:`quick-start` - Create your first WebSocket consumer
* :doc:`user-guide/index` - Explore the user guide for detailed information
