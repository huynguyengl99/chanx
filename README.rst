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

The missing toolkit for WebSocket development — supporting Django Channels, FastAPI, and any ASGI-compatible framework with decorator-based handlers, automatic AsyncAPI documentation generation, authentication, logging, and structured messaging.

Installation
------------

**Basic Installation (Core Only)**

.. code-block:: bash

    pip install chanx

**For Django Channels Projects**

.. code-block:: bash

    pip install "chanx[channels]"

**For FastAPI and Other ASGI Frameworks**

.. code-block:: bash

    pip install "chanx[fast_channels]"

For complete documentation, visit `chanx docs <https://chanx.readthedocs.io/>`_.

Introduction
------------

Building real-time WebSocket applications shouldn't require reinventing the wheel for each framework. Chanx brings
consistency, type safety, and powerful tooling to WebSocket development across Django Channels, FastAPI, and any
ASGI-compatible framework.

With Chanx, you get decorator-based message handlers that automatically generate type-safe routing, Pydantic validation,
and AsyncAPI 3.0 documentation. Whether you're building a chat system, live notifications, or real-time collaboration
features, Chanx provides the missing pieces that make WebSocket development as straightforward as building REST APIs.

Quick Look
----------

See how Chanx works with decorator-based handlers. Define your WebSocket consumer with ``@ws_handler`` for client messages and ``@event_handler`` for server-side events:

.. code-block:: python

    from typing import Literal
    from pydantic import BaseModel
    from chanx.core.decorators import ws_handler, event_handler, channel
    from chanx.core.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage
    from chanx.messages.base import BaseMessage

    # Define your message types
    class ChatPayload(BaseModel):
        message: str

    class ChatMessage(BaseMessage):
        action: Literal["chat"] = "chat"
        payload: ChatPayload

    class ChatNotificationMessage(BaseMessage):
        action: Literal["chat_notification"] = "chat_notification"
        payload: ChatPayload

    class NotificationPayload(BaseModel):
        alert: str

    class NotificationEvent(BaseMessage):
        action: Literal["notification_event"] = "notification_event"
        payload: NotificationPayload

    class NotificationMessage(BaseMessage):
        action: Literal["notification"] = "notification"
        payload: NotificationPayload

    @channel(name="chat", description="Real-time chat API")
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        @ws_handler(summary="Handle ping requests")
        async def handle_ping(self, message: PingMessage) -> PongMessage:
            return PongMessage()

        @ws_handler(
            summary="Handle chat messages",
            output_type=ChatNotificationMessage,
        )
        async def handle_chat(self, message: ChatMessage) -> None:
            # Broadcast to all clients in group
            await self.broadcast_message(
                ChatNotificationMessage(
                    payload=ChatPayload(message=f"User: {message.payload.message}")
                )
            )

        @event_handler(output_type=NotificationMessage)
        async def handle_notification(self, event: NotificationEvent) -> NotificationMessage:
            """Handle notifications from background workers."""
            return NotificationMessage(payload=event.payload)

**Client Usage:**

.. code-block:: javascript

    // Send a ping - client receives immediate response
    websocket.send(JSON.stringify({"action": "ping"}))
    // Receives: {"action": "pong", "payload": null}

    // Send a chat message - all clients in group receive broadcast
    websocket.send(JSON.stringify({
        "action": "chat",
        "payload": {"message": "Hello everyone!"}
    }))
    // All clients receive: {"action": "chat_notification", "payload": {"message": "User: Hello everyone!"}}

**Send events from anywhere in your application:**

.. code-block:: python

    # From Django views, Celery tasks, management scripts, etc.
    ChatConsumer.broadcast_event_sync(
        NotificationEvent(payload={"alert": "Server maintenance starting"}),
        groups=["chat_room"]
    )
    # All WebSocket clients receive: {"action": "notification", "payload": {"alert": "..."}}

The framework automatically discovers your handlers, validates messages with Pydantic, and generates AsyncAPI documentation.

Key Features & Components
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Multi-Framework Support**: Works with Django Channels, FastAPI, and any ASGI-compatible framework via ``chanx.ext.channels`` and ``chanx.ext.fast_channels``
- **Decorator-Based Architecture**: Use ``@ws_handler``, ``@event_handler``, and ``@channel`` decorators with automatic message routing and validation
- **AsyncAPI Documentation**: Generate AsyncAPI 3.0 specifications automatically from decorated handlers and message types
- **Type-Safe Messaging**: Pydantic-based validation with automatic discriminated unions and full mypy/pyright support
- **Authentication System**: DRF integration for Django, flexible authenticator base classes for other frameworks
- **Channel Layer Integration**: Type-safe pub/sub messaging, group broadcasting, and event handling across your application
- **Comprehensive Testing**: Framework-specific test utilities for WebSocket consumers and group messaging
- **Production Features**: Structured logging, error handling, and battle-tested patterns for scalable applications


Type Parameters and AsyncAPI Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The framework automatically generates AsyncAPI 3.0 specifications from your decorated handlers. You can specify
event types for type safety:

.. code-block:: python

    @channel(name="chat", description="Real-time chat system", tags=["chat"])
    class ChatConsumer(AsyncJsonWebsocketConsumer[NotificationEvent]):
        @ws_handler(
            summary="Handle chat messages",
            description="Process chat messages and broadcast to room",
            output_type=ChatNotificationMessage,
        )
        async def handle_chat(self, message: ChatMessage) -> None:
            await self.broadcast_message(
                ChatNotificationMessage(
                    payload=ChatPayload(message=f"💬 {message.payload.message}")
                ),
            )

        @event_handler
        async def handle_notification(self, event: NotificationEvent) -> NotificationMessage:
            return NotificationMessage(payload=event.payload)

Sending Events and Broadcasting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Send events to specific consumers or broadcast to groups:

.. code-block:: python

    # Send event to specific channel
    await MyConsumer.send_event(
        NotificationEvent(payload="Hello!"),
        channel_name="specific.channel.name"
    )

    # Broadcast event to group
    await MyConsumer.broadcast_event(
        SystemNotify(payload="Server maintenance in 5 minutes"),
        groups=["admin_users"]
    )

Configuration
-------------

Django Configuration
~~~~~~~~~~~~~~~~~~~~~

For Django projects, configure Chanx through the ``CHANX`` dictionary in your Django settings:

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
        'LOG_WEBSOCKET_MESSAGE': True,  # Whether to log WebSocket messages
        'LOG_IGNORED_ACTIONS': [],  # Message actions that should not be logged
    }

Other Frameworks Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For FastAPI and other ASGI frameworks, configure Chanx by subclassing ``AsyncJsonWebsocketConsumer`` and setting class attributes:

.. code-block:: python

    from chanx.core.websocket import AsyncJsonWebsocketConsumer

    class BaseConsumer(AsyncJsonWebsocketConsumer):
        # Message configuration
        camelize = False  # Whether to camelize/decamelize messages
        send_completion = False  # Whether to send completion messages
        send_message_immediately = True  # Whether to yield control after sending
        log_websocket_message = True  # Whether to log WebSocket messages
        log_ignored_actions = []  # Message actions to ignore in logs

        # Channel layer configuration
        channel_layer_alias = "default"  # Channel layer alias to use

You can also configure per-consumer by setting attributes directly:

.. code-block:: python

    @channel(name="chat")
    class ChatConsumer(BaseConsumer):
        send_completion = True  # Override base setting
        log_ignored_actions = ["ping", "pong"]  # Don't log ping/pong messages


Learn More
----------

* `Django Quick Start <https://chanx.readthedocs.io/en/latest/quick-start-django.html>`_ - Django setup instructions
* `FastAPI Quick Start <https://chanx.readthedocs.io/en/latest/quick-start-fastapi.html>`_ - FastAPI setup instructions
* `User Guide <https://chanx.readthedocs.io/en/latest/user-guide/prerequisites.html>`_ - Comprehensive feature documentation
* `API Reference <https://chanx.readthedocs.io/en/latest/reference/core.html>`_ - Detailed API documentation
* `Django Examples <https://chanx.readthedocs.io/en/latest/examples/django.html>`_ - Django implementation examples
* `FastAPI Examples <https://chanx.readthedocs.io/en/latest/examples/fastapi.html>`_ - FastAPI implementation examples
