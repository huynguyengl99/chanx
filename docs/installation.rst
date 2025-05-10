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

Or install from source:

.. code-block:: bash

    git clone https://github.com/huynguyengl99/chanx.git
    cd chanx
    pip install -e .

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
