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

A batteries-included WebSocket framework for Django Channels, FastAPI, and ASGI-based applications. Chanx provides automatic message routing, Pydantic validation, type safety, AsyncAPI documentation generation, and comprehensive testing utilities out of the box.

Why Use Chanx?
--------------

**Without Chanx** - Manual routing, validation, and documentation:

.. code-block:: python

    # Django Channels - manual routing
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "chat":
            if "message" not in data.get("payload", {}):
                await self.send(json.dumps({"error": "Missing message"}))
                return
            # Handle chat...
        elif action == "ping":
            await self.send(json.dumps({"action": "pong"}))
        # ... endless if-else chains

    # FastAPI - manual routing, no broadcasting, no groups
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "chat":
                if "message" not in data.get("payload", {}):
                    await websocket.send_json({"error": "Missing message"})
                    continue
                # No broadcasting, must manually track connections
                # No type safety, no validation, no documentation
            elif action == "ping":
                await websocket.send_json({"action": "pong"})
            # ... more manual handling

**With Chanx** - Automatic routing, validation, and type safety:

.. code-block:: python

    @ws_handler(output_type=ChatNotificationMessage)
    async def handle_chat(self, message: ChatMessage) -> None:
        # Automatically routed, validated, and type-safe
        await self.broadcast_message(
            ChatNotificationMessage(payload=message.payload)
        )

    @ws_handler
    async def handle_ping(self, message: PingMessage) -> PongMessage:
        return PongMessage()  # Auto-documented in AsyncAPI

**What Chanx Eliminates:**

*Technical Pain Points:*

- Manual if-else routing chains → Automatic routing via decorators + Pydantic discriminated unions
- Manual validation code → Pydantic ``validate_python()`` with type-safe models
- Runtime type surprises → Catch errors during development with mypy/pyright static checking
- Writing API docs → Auto-generated AsyncAPI 3.0 specs
- Framework lock-in → Single codebase works with both Django Channels and FastAPI
- Testing complexity → Comprehensive testing utilities

*Team Collaboration Nightmares:*

- Inconsistent implementations → Enforced patterns via decorators and type-safe messages
- Painful code reviews → Clean, declarative handlers instead of nested if-else chains
- Slow onboarding → Self-documenting code with AsyncAPI specs as single source of truth
- No API contract → Auto-generated AsyncAPI documentation for frontend teams
- Fragile tests → Built-in testing utilities with standardized patterns
- Debugging hell → Structured logging with automatic request/response tracing

Built on years of real-world WebSocket development experience, Chanx provides proven patterns that help teams ship faster, maintain cleaner code, and reduce debugging time.

Installation
------------

**For Django Channels Projects**

.. code-block:: bash

    pip install "chanx[channels]"

**For FastAPI and Other ASGI Frameworks**

.. code-block:: bash

    pip install "chanx[fast_channels]"

**For Client Generator CLI**

.. code-block:: bash

    pip install "chanx[cli]"

**For Using Generated Clients**

.. code-block:: bash

    pip install "chanx[client]"


Prerequisites
-------------

**For Django**: Ensure Django Channels is properly set up. See `Django Channels documentation <https://channels.readthedocs.io/>`_.

**For FastAPI**: Ensure fast-channels is properly set up. See `fast-channels documentation <https://fast-channels.readthedocs.io/en/latest/index.html>`_.

Quick Start
-----------

**1. Define Message Types with Discriminated Action Field**

Create message types using Pydantic with a ``Literal`` action field for automatic routing:

.. code-block:: python

    from typing import Literal
    from pydantic import BaseModel
    from chanx.messages.base import BaseMessage

    # Define message payloads
    class ChatPayload(BaseModel):
        message: str

    # Incoming message from client
    class ChatMessage(BaseMessage):
        action: Literal["chat"] = "chat"
        payload: ChatPayload

    # Outgoing notification to clients
    class ChatNotificationMessage(BaseMessage):
        action: Literal["chat_notification"] = "chat_notification"
        payload: ChatPayload

**2. Create WebSocket Consumer**

Use decorators to define handlers that automatically route and validate messages:

.. code-block:: python

    from chanx.core.decorators import ws_handler, channel

    # For Django
    from chanx.channels.websocket import AsyncJsonWebsocketConsumer

    # For FastAPI
    # from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer

    @channel(name="chat", description="Real-time chat API")
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        groups = ["chat_room"]  # Auto-join this group on connect

        @ws_handler(
            summary="Handle chat messages",
            output_type=ChatNotificationMessage
        )
        async def handle_chat(self, message: ChatMessage) -> None:
            # Broadcast to all clients in the group
            await self.broadcast_message(
                ChatNotificationMessage(
                    payload=ChatPayload(message=f"User: {message.payload.message}")
                )
            )

**3. Setup Routing**

**For Django:**

.. code-block:: python

    # yourapp/routing.py
    from chanx.channels.routing import path
    from channels.routing import URLRouter
    from .consumers import ChatConsumer

    router = URLRouter([
        path("chat/", ChatConsumer.as_asgi()),
    ])

    # config/asgi.py
    from channels.routing import ProtocolTypeRouter
    from chanx.channels.routing import include
    from django.core.asgi import get_asgi_application

    django_asgi_app = get_asgi_application()

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": include("yourapp.routing"),
    })

**For FastAPI:**

.. code-block:: python

    # main.py
    from fastapi import FastAPI
    from .consumers import ChatConsumer

    app = FastAPI()

    # Create WebSocket sub-app
    ws_router = FastAPI()
    ws_router.add_websocket_route("/chat", ChatConsumer.as_asgi())

    # Mount WebSocket routes
    app.mount("/ws", ws_router)

**4. Run Server**

**Django** (with Daphne or Uvicorn):

.. code-block:: bash

    # Using Daphne
    daphne config.asgi:application

    # Or using Uvicorn
    uvicorn config.asgi:application

**FastAPI**:

.. code-block:: bash

    uvicorn main:app

**5. Client Usage**

Connect from JavaScript and send/receive typed messages:

.. code-block:: javascript

    const ws = new WebSocket('ws://localhost:8000/ws/chat')

    // Send message - automatically validated and routed
    ws.send(JSON.stringify({
        "action": "chat",
        "payload": {"message": "Hello everyone!"}
    }))

    // Receive broadcast
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        // {"action": "chat_notification", "payload": {"message": "User: Hello everyone!"}}
        console.log(data.payload.message)
    }

**6. Add AsyncAPI Documentation**

**For Django:**

.. code-block:: python

    # config/urls.py (your main urls.py)
    from django.urls import path, include

    urlpatterns = [
        # ... other patterns
        path("asyncapi/", include("chanx.channels.urls")),
    ]

**For FastAPI:**

.. code-block:: python

    from chanx.fast_channels import asyncapi_docs, asyncapi_spec_json
    from chanx.fast_channels.type_defs import AsyncAPIConfig

    config = AsyncAPIConfig(
        description="WebSocket API documentation",
        version="1.0.0"
    )

    @app.get("/asyncapi")
    async def docs(request: Request):
        return await asyncapi_docs(request=request, app=app, config=config)

    @app.get("/asyncapi.json")
    async def spec(request: Request):
        return await asyncapi_spec_json(request=request, app=app, config=config)

Visit ``/asyncapi/`` to see your auto-generated interactive documentation.

Configuration
-------------

**Django** - Configure via ``settings.py``:

.. code-block:: python

    # settings.py
    CHANX = {
        # Message handling
        'MESSAGE_ACTION_KEY': 'action',  # Discriminator field name
        'CAMELIZE': False,  # Convert snake_case to camelCase for JS clients
        'SEND_COMPLETION': False,  # Send completion message after handling
        'SEND_MESSAGE_IMMEDIATELY': True,  # Yield control after sending
        'SEND_AUTHENTICATION_MESSAGE': True,  # Send auth status after connect

        # Logging
        'LOG_WEBSOCKET_MESSAGE': True,  # Log WebSocket messages
        'LOG_IGNORED_ACTIONS': [],  # Actions to exclude from logging

        # WebSocket
        'WEBSOCKET_BASE_URL': None,  # Override WebSocket URL

        # AsyncAPI documentation
        'ASYNCAPI_TITLE': 'AsyncAPI Documentation',
        'ASYNCAPI_DESCRIPTION': '',
        'ASYNCAPI_VERSION': '1.0.0',
        'ASYNCAPI_SERVER_URL': None,
        'ASYNCAPI_SERVER_PROTOCOL': None,
    }

**FastAPI** - Configure via class attributes (can also be used per-consumer in Django):

.. code-block:: python

    from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer

    class BaseConsumer(AsyncJsonWebsocketConsumer):
        # Message handling
        camelize = False
        discriminator_field = "action"
        send_completion = False
        send_message_immediately = True

        # Logging
        log_websocket_message = False
        log_ignored_actions = []

        # Channel layer (FastAPI)
        channel_layer_alias = "default"

**Per-Consumer Override** (Django):

.. code-block:: python

    @channel(name="chat")
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        # Override global settings for this consumer
        send_completion = True
        log_ignored_actions = ["ping", "pong"]

Key Features
------------

**Decorator-Based Handlers**
  ``@ws_handler`` for WebSocket messages, ``@event_handler`` for channel events, ``@channel`` for consumer metadata

**Discriminated Union Routing**
  Automatic message type detection and routing using Pydantic's discriminator field pattern

**AsyncAPI 3.0 Generation**
  Auto-generate interactive documentation and OpenAPI-style specs from decorated handlers

**Type-Safe Client Generator**
  Generate Python WebSocket clients from AsyncAPI schemas with full type safety and IDE support

**Authentication System**
  Built-in ``DjangoAuthenticator`` with DRF permission support, extensible ``BaseAuthenticator`` for custom flows

**Channel Layer Integration**
  Type-safe ``broadcast_message()``, ``send_event()``, and ``broadcast_event()`` with full validation

**Testing Utilities**
  Framework-specific ``WebsocketCommunicator`` wrappers and test helpers for end-to-end WebSocket testing

**Structured Logging**
  Automatic request/response logging with ``structlog``, configurable action filtering, error tracing

**Configuration Management**
  Django settings integration via ``CHANX`` dict, class-level config for FastAPI consumers

Client Generator
----------------

Generate type-safe Python clients from your AsyncAPI schema:

.. code-block:: bash

    # Generate from local file (JSON or YAML)
    chanx generate-client --schema asyncapi.json --output ./my_client
    chanx generate-client --schema asyncapi.yaml --output ./my_client

    # Generate directly from URL (no need to download)
    chanx generate-client --schema http://localhost:8000/asyncapi.json --output ./my_client

.. code-block:: python

    # Use generated client with full type safety
    from my_client.chat import ChatClient, ChatMessage, ChatPayload

    client = ChatClient("localhost:8000")

    await client.send_message(
        ChatMessage(payload=ChatPayload(message="Hello!"))
    )

Learn More
----------

* `Documentation <https://chanx.readthedocs.io/>`_ - Complete guide and API reference
* `Django Quick Start <https://chanx.readthedocs.io/en/latest/quick-start-django.html>`_ - Django-specific setup
* `FastAPI Quick Start <https://chanx.readthedocs.io/en/latest/quick-start-fastapi.html>`_ - FastAPI-specific setup
* `User Guide <https://chanx.readthedocs.io/en/latest/user-guide/prerequisites.html>`_ - In-depth features and patterns
* `Client Generator Guide <https://chanx.readthedocs.io/en/latest/user-guide/client-generator.html>`_ - Generate type-safe clients
* `Examples <https://chanx.readthedocs.io/en/latest/examples/django.html>`_ - Real-world implementation examples
