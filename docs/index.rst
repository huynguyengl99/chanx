Welcome to Chanx Documentation
==============================
**Chanx**: The enhanced toolkit for Django Channels
---------------------------------------------------
Chanx provides a robust framework for building WebSocket applications in Django with authentication,
structured messaging, and testing capabilities. It builds on Django Channels to offer a more complete
solution for real-time features.

.. image:: /_static/interrogate_badge.svg
   :target: https://github.com/huynguyengl99/chanx
   :alt: Documentation Coverage


Key Features
------------
* **DRF-style Authentication**: Use Django REST Framework authentication for WebSockets
* **Structured Messaging**: Type-safe message handling with Pydantic validation
* **Group Management**: Automatic channel group management for pub/sub messaging
* **Enhanced URL Routing**: Extended routing utilities for WebSocket endpoints
* **Testing Utilities**: Simplified WebSocket testing infrastructure
* **Playground UI**: Interactive WebSocket exploration and testing tool

Getting Started
---------------
.. code-block:: bash

    pip install chanx

.. code-block:: python

    # settings.py
    INSTALLED_APPS = [
        # ...
        'chanx',
        'channels',
        # ...
    ]

Quick Example
-------------
.. code-block:: python

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.incoming import IncomingMessage
    from chanx.messages.outgoing import PongMessage
    from chanx.urls import path

    class EchoConsumer(AsyncJsonWebsocketConsumer):
        INCOMING_MESSAGE_SCHEMA = IncomingMessage

        async def receive_message(self, message, **kwargs):
            # Echo back with a pong
            await self.send_message(PongMessage())

    # Define URL patterns
    router = [
        path('ws/echo/', EchoConsumer.as_asgi()),
    ]

Contents
--------
.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   introduction
   installation
   quick-start

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user-guide/index
   user-guide/authentication
   user-guide/consumers
   user-guide/messages
   user-guide/testing
   user-guide/playground

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   reference/generic
   reference/messages
   reference/urls
   reference/routing
   reference/utils
   reference/settings

.. toctree::
   :maxdepth: 1
   :caption: Examples

   examples/index
   examples/basic
   examples/chat
   examples/dashboard

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog
