CHANX (CHANnels-eXtension)
==========================
.. image:: https://img.shields.io/pypi/v/chanx
   :target: https://pypi.org/project/chanx/
   :alt: PyPI

.. image:: https://codecov.io/gh/huynguyengl99/chanx/branch/main/graph/badge.svg?token=X8R3BDPTY6
   :target: https://codecov.io/gh/huynguyengl99/chanx
   :alt: Code Coverage

.. image:: https://github.com/huynguyengl99/chanx/actions/workflows/test.yml/badge.svg?branch=main
   :target: https://github.com/huynguyengl99/chanx/actions/workflows/test.yml
   :alt: Test

.. image:: https://www.mypy-lang.org/static/mypy_badge.svg
   :target: https://mypy-lang.org/
   :alt: Checked with mypy

.. image:: https://microsoft.github.io/pyright/img/pyright_badge.svg
   :target: https://microsoft.github.io/pyright/
   :alt: Checked with pyright


.. image:: https://chanx.readthedocs.io/en/latest/_static/interrogate_badge.svg
   :target: https://github.com/huynguyengl99/chanx
   :alt: Interrogate Badge

The missing toolkit for Django Channels — authentication, logging, structured messaging, and more.

Installation
------------

.. code-block:: bash

    pip install chanx

For complete documentation, visit `chanx docs <https://chanx.readthedocs.io/>`_.

Introduction
------------

Django Channels provides excellent WebSocket support for Django applications, but leaves gaps in authentication,
structured messaging, and developer tooling. Chanx fills these gaps with a comprehensive toolkit that makes
building WebSocket applications simpler and more maintainable.

Key Features
~~~~~~~~~~~~

- **REST Framework Integration**: Use DRF authentication and permission classes with WebSockets
- **Structured Messaging**: Type-safe message handling with Pydantic validation and generic type parameters
- **WebSocket Playground**: Interactive UI for testing WebSocket endpoints
- **Group Management**: Simplified pub/sub messaging with automatic group handling
- **Typed Channel Events**: Type-safe channel layer events
- **Channels-friendly Routing**: Django-like ``path``, ``re_path``, and ``include`` functions designed specifically for WebSocket routing
- **Comprehensive Logging**: Structured logging for WebSocket connections and messages
- **Error Handling**: Robust error reporting and client feedback
- **Testing Utilities**: Specialized tools for testing WebSocket consumers
- **Multi-user Testing Support**: Test group broadcasting and concurrent connections
- **Object-level Permissions**: Support for DRF object-level permission checks
- **Full Type Hints**: Complete mypy and pyright support for better IDE integration and type safety

Core Components
~~~~~~~~~~~~~~~

- **AsyncJsonWebsocketConsumer**: Base consumer with authentication, structured messaging, and typed events
- **ChanxWebsocketAuthenticator**: Bridges WebSockets with DRF authentication
- **Message System**: Type-safe message classes with automatic validation and generic type parameters
- **Channel Event System**: Type-safe channel layer events
- **WebSocket Routing**: Django-style routing functions (``path``, ``re_path``, ``include``) optimized for Channels
- **WebSocketTestCase**: Test utilities for WebSocket consumers
- **Generic Type Safety**: Compile-time type checking with generic parameters for messages, events, and models

Using Generic Type Parameters
-----------------------------
AsyncJsonWebsocketConsumer uses three generic type parameters for improved type safety:

.. code-block:: python

    class AsyncJsonWebsocketConsumer[IC, Event, M]:
        """
        Typed WebSocket consumer with three generic parameters:

        IC: Incoming message type (required) - Union of BaseMessage subclasses
        Event: Channel event type (optional) - Union of BaseChannelEvent subclasses or None
        M: Model type (optional) - Django model for object-level permissions
        """

You can use these parameters in different combinations:

.. code-block:: python

    # Minimal usage - just specify incoming message type
    class SimpleConsumer(AsyncJsonWebsocketConsumer[PingMessage]):
        async def receive_message(self, message: PingMessage, **kwargs: Any) -> None:
            # message is properly typed as PingMessage
            ...

    # With incoming messages and events
    class EventConsumer(AsyncJsonWebsocketConsumer[ChatMessage, ChatEvent]):
        async def receive_message(self, message: ChatMessage, **kwargs: Any) -> None:
            # Handle incoming messages
            ...

        async def receive_event(self, event: ChatEvent) -> None:
            # Handle typed events using pattern matching
            match event:
                case NotifyEvent():
                    # Process the notification event
                    await self.send_message(ResponseMessage(payload=event.payload))
                case _:
                    pass

    # With group messaging
    class GroupConsumer(AsyncJsonWebsocketConsumer[ChatMessage]):
        async def receive_message(self, message: ChatMessage, **kwargs: Any) -> None:
            # Send typed group messages using send_group_message
            group_msg = MemberMessage(payload={"content": "Hello group!"})
            await self.send_group_message(group_msg)

    # Complete example with all generic parameters
    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatMessage, ChatEvent, Room]):
        # Room is used for object-level permissions
        queryset = Room.objects.all()

        async def build_groups(self) -> list[str]:
            # self.obj is typed as Room
            return [f"room_{self.obj.id}"]

Making Parameters Optional
~~~~~~~~~~~~~~~~~~~~~~~~~~
For parameters you don't need, use None:

.. code-block:: python

    # No events, with model
    class ModelConsumer(AsyncJsonWebsocketConsumer[ChatMessage, None, Room]):
        ...

    # With events, no model
    class EventOnlyConsumer(AsyncJsonWebsocketConsumer[ChatMessage, ChatEvent]):
        ...

Configuration
-------------

Chanx can be configured through the ``CHANX`` dictionary in your Django settings. Below is a complete list
of available settings with their default values and descriptions:

.. code-block:: python

    # settings.py
    CHANX = {
        # Message configuration
        'MESSAGE_ACTION_KEY': 'action',  # Key name for action field in messages
        'CAMELIZE': False,  # Whether to camelize/decamelize messages for JavaScript clients

        # Completion messages
        'SEND_COMPLETION': False,  # Whether to send completion message after processing messages

        # Messaging behavior
        'SEND_MESSAGE_IMMEDIATELY': True,  # Whether to yield control after sending messages
        'SEND_AUTHENTICATION_MESSAGE': True,  # Whether to send auth status after connection

        # Logging configuration
        'LOG_RECEIVED_MESSAGE': True,  # Whether to log received messages
        'LOG_SENT_MESSAGE': True,  # Whether to log sent messages
        'LOG_IGNORED_ACTIONS': [],  # Message actions that should not be logged

        # Playground configuration
        'WEBSOCKET_BASE_URL': 'ws://localhost:8000'  # Default WebSocket URL for discovery
    }

WebSocket Routing
-----------------

Chanx provides Django-style routing functions specifically designed for WebSocket applications. These functions work similarly to Django's URL routing but are optimized for Channels and ASGI applications.

**Key principles:**

- Use ``chanx.routing`` for WebSocket routes in your ``routing.py`` files
- Use ``django.urls`` for HTTP routes in your ``urls.py`` files
- Maintain clear separation between HTTP and WebSocket routing

**Available functions:**

- ``path()``: Create URL patterns with path converters (e.g., ``'<int:id>/'``)
- ``re_path()``: Create URL patterns with regular expressions
- ``include()``: Include routing patterns from other modules

**Example routing setup:**

.. code-block:: python

    # app/routing.py
    from chanx.routing import path, re_path
    from . import consumers

    router = URLRouter([
        path("", consumers.MyConsumer.as_asgi()),
        path("room/<str:room_name>/", consumers.RoomConsumer.as_asgi()),
        re_path(r"^admin/(?P<id>\d+)/$", consumers.AdminConsumer.as_asgi()),
    ])

    # project/routing.py
    from chanx.routing import include, path
    from channels.routing import URLRouter

    router = URLRouter([
        path("ws/", URLRouter([
            path("app/", include("app.routing")),
            path("chat/", include("chat.routing")),
        ])),
    ])

WebSocket Playground
--------------------

Add the playground to your URLs and explore your WebSocket endpoints interactively:

.. code-block:: python

    urlpatterns = [
        path('playground/', include('chanx.playground.urls')),
    ]

Visit ``/playground/websocket/`` to test your endpoints without writing JavaScript.

Complete Example Project
------------------------

For a full production-ready implementation with advanced patterns and deployment configurations, check out the complete example project:

**GitHub Repository**: `chanx-example <https://github.com/huynguyengl99/chanx-example>`_

This repository demonstrates:

- Production deployment configurations
- Advanced authentication patterns
- Group messaging and channel events
- Comprehensive testing strategies
- Real-world usage patterns

Learn More
----------

* `Quick Start Guide <https://chanx.readthedocs.io/en/latest/quick-start.html>`_ - Step-by-step setup instructions
* `User Guide <https://chanx.readthedocs.io/en/latest/user-guide/index.html>`_ - Comprehensive feature documentation
* `API Reference <https://chanx.readthedocs.io/en/latest/reference/index.html>`_ - Detailed API documentation
* `Examples <https://chanx.readthedocs.io/en/latest/examples/index.html>`_ - Real-world usage examples
