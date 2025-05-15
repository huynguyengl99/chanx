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
- **Structured Messaging**: Type-safe message handling with Pydantic validation
- **WebSocket Playground**: Interactive UI for testing WebSocket endpoints
- **Group Management**: Simplified pub/sub messaging with automatic group handling
- **Channels-friendly Routing**: Django-like ``path``, ``re_path``, and ``include`` functions designed specifically for WebSocket routing
- **Comprehensive Logging**: Structured logging for WebSocket connections and messages
- **Error Handling**: Robust error reporting and client feedback
- **Testing Utilities**: Specialized tools for testing WebSocket consumers
- **Multi-user Testing Support**: Test group broadcasting and concurrent connections
- **Object-level Permissions**: Support for DRF object-level permission checks
- **Full Type Hints**: Complete mypy and pyright support for better IDE integration and type safety

Core Components
~~~~~~~~~~~~~~~

- **AsyncJsonWebsocketConsumer**: Base consumer with authentication and structured messaging
- **ChanxWebsocketAuthenticator**: Bridges WebSockets with DRF authentication
- **Message System**: Type-safe message classes with automatic validation
- **WebSocket Routing**: Django-style routing functions (``path``, ``re_path``, ``include``) optimized for Channels
- **WebSocketTestCase**: Test utilities for WebSocket consumers
- **Discriminated Union Messages**: Runtime validation of message types with action discriminator

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

Example: Building an Assistant App
----------------------------------

Let's create a simple assistant chatbot with authentication:

1. First, create a new Django app for your assistant:

.. code-block:: bash

    python manage.py startapp assistants

2. Define your message types in ``assistants/messages/assistant.py``:

.. code-block:: python

    from typing import Literal

    from chanx.messages.base import BaseIncomingMessage, BaseMessage
    from chanx.messages.incoming import PingMessage
    from pydantic import BaseModel


    class MessagePayload(BaseModel):
        content: str


    class NewMessage(BaseMessage):
        """
        New message for assistant.
        """
        action: Literal["new_message"] = "new_message"
        payload: MessagePayload


    class ReplyMessage(BaseMessage):
        action: Literal["reply"] = "reply"
        payload: MessagePayload


    class AssistantIncomingMessage(BaseIncomingMessage):
        message: NewMessage | PingMessage

3. Create your consumer in ``assistants/consumers.py``:

.. code-block:: python

    from typing import Any

    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    from assistants.messages.assistant import (
        AssistantIncomingMessage,
        MessagePayload,
        NewMessage,
        ReplyMessage,
    )


    class AssistantConsumer(AsyncJsonWebsocketConsumer):
        """Websocket to chat with server, like chat with chatbot system"""

        INCOMING_MESSAGE_SCHEMA = AssistantIncomingMessage
        permission_classes = [IsAuthenticated]

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
            match message:
                case PingMessage():
                    # Reply with a PONG message
                    await self.send_message(PongMessage())
                case NewMessage(payload=new_message_payload):
                    # Echo back with a reply message
                    await self.send_message(
                        ReplyMessage(
                            payload=MessagePayload(
                                content=f"Reply: {new_message_payload.content}"
                            )
                        )
                    )
                case _:
                    pass

4. Set up WebSocket routing in ``assistants/routing.py``:

.. code-block:: python

    from channels.routing import URLRouter

    from chanx.routing import path

    from assistants.consumers import AssistantConsumer

    router = URLRouter(
        [
            path("", AssistantConsumer.as_asgi()),
        ]
    )

5. Create a project-level routing file in your project's root directory (same level as urls.py) as ``routing.py``:

.. code-block:: python

    from channels.routing import URLRouter

    from chanx.routing import include, path

    ws_router = URLRouter(
        [
            path("assistants/", include("assistants.routing")),
            # Add other WebSocket routes here
        ]
    )

    router = URLRouter(
        [
            path("ws/", include(ws_router)),
        ]
    )

6. Configure your project's ``asgi.py`` to use the WebSocket routing:

.. code-block:: python

    import os

    from channels.routing import ProtocolTypeRouter
    from channels.security.websocket import OriginValidator
    from channels.sessions import CookieMiddleware
    from django.conf import settings
    from django.core.asgi import get_asgi_application

    from chanx.routing import include

    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yourproject.settings")
    django_asgi_app = get_asgi_application()

    # Set up protocol routing
    routing = {
        "http": django_asgi_app,
        "websocket": OriginValidator(
            CookieMiddleware(include("yourproject.routing")),
            settings.CORS_ALLOWED_ORIGINS + settings.CSRF_TRUSTED_ORIGINS,
        ),
    }

    application = ProtocolTypeRouter(routing)

7. Ensure your settings.py has the required settings:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'channels',
        'chanx',
        'assistants',
        # ...
    ]

    # For WebSocket origin validation
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8000",
        # Add other trusted origins
    ]

8. Connect from your JavaScript client:

.. code-block:: javascript

    const socket = new WebSocket('ws://localhost:8000/ws/assistants/');

    // Add authentication headers
    socket.onopen = function() {
        console.log('Connected to assistant');

        // Send a message
        socket.send(JSON.stringify({
            action: 'new_message',
            payload: {
                content: 'Hello assistant!'
            }
        }));
    };

    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);

        if (data.action === 'reply') {
            console.log('Assistant replied:', data.payload.content);
        }
    };

If you don't have a client application ready, you can use the WebSocket Playground (covered in the next section) to test your assistant endpoint without writing any JavaScript.

WebSocket Playground
--------------------

Add the playground to your URLs:

.. code-block:: python

    urlpatterns = [
        path('playground/', include('chanx.playground.urls')),
    ]

Then visit ``/playground/websocket/`` to explore and test your WebSocket endpoints. The playground will automatically
discover all registered WebSocket routes from your ``routing.py`` file, including any nested routes from included routers.

Testing
-------

Chanx provides specialized testing utilities for WebSocket consumers. For optimal testing, configure your test settings:

.. code-block:: python

    # settings/test.py
    CHANX = {
        "SEND_COMPLETION": True,  # Essential for receive_all_json() to work properly
        "SEND_AUTHENTICATION_MESSAGE": True,  # Recommended for testing auth flows
        "LOG_RECEIVED_MESSAGE": False,  # Optional: reduce test output
        "LOG_SENT_MESSAGE": False,  # Optional: reduce test output
    }

**Important**: Setting ``SEND_COMPLETION: True`` is crucial for testing, as the ``receive_all_json()`` method relies on completion messages to know when to stop collecting messages.

Write tests for your WebSocket consumers:

.. code-block:: python

    from chanx.testing import WebsocketTestCase
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    class TestChatConsumer(WebsocketTestCase):
        ws_path = "/ws/chat/room1/"

        async def test_connection_and_ping(self) -> None:
            # Connect and authenticate
            await self.auth_communicator.connect()
            await self.auth_communicator.assert_authenticated_status_ok()

            # Test ping/pong functionality
            await self.auth_communicator.send_message(PingMessage())
            messages = await self.auth_communicator.receive_all_json()
            assert messages == [PongMessage().model_dump()]

        async def test_multi_user_scenario(self) -> None:
            # Create communicators for multiple users
            first_comm = self.auth_communicator
            second_comm = self.create_communicator(headers=self.get_headers_for_user(user2))

            # Connect both
            await first_comm.connect()
            await second_comm.connect()

            # Test group broadcasting
            # ...
