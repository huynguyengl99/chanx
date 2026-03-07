Handler Mixins
==============

Chanx supports composing reusable handler logic via Python mixin classes. A mixin is a plain class that defines ``@ws_handler`` or ``@event_handler`` methods — when mixed into a consumer through multiple inheritance, its handlers are automatically discovered and available for message routing and AsyncAPI documentation.

WebSocket Handler Mixin
-----------------------

A WebSocket handler mixin defines ``@ws_handler`` methods that handle incoming client messages:

.. code-block:: python

    from typing import Literal

    from chanx.core.decorators import ws_handler
    from chanx.messages.base import BaseMessage


    # Define message types for the mixin
    class ExtraRequestMessage(BaseMessage):
        action: Literal["extra_request"] = "extra_request"
        payload: str


    class ExtraResponseMessage(BaseMessage):
        action: Literal["extra_response"] = "extra_response"
        payload: str


    # Define the mixin
    class ExtraWsHandlerMixin:
        @ws_handler(
            summary="Handle extra request",
            description="Simple extra message",
        )
        async def handle_extra_message(
            self, message: ExtraRequestMessage
        ) -> ExtraResponseMessage:
            return ExtraResponseMessage(payload=message.payload + " any extra thing")

Compose the mixin into a consumer using multiple inheritance:

.. code-block:: python

    class ChatConsumer(ExtraWsHandlerMixin, AsyncJsonWebsocketConsumer):
        @ws_handler(summary="Handle ping")
        async def handle_ping(self, _message: PingMessage) -> PongMessage:
            return PongMessage()

``ChatConsumer`` now handles both ``ping`` and ``extra_request`` messages.

Event Handler Mixin
-------------------

An event handler mixin defines ``@event_handler`` methods that handle channel layer events:

.. code-block:: python

    from chanx.core.decorators import event_handler
    from chanx.messages.base import BaseMessage


    class ExtraEventMessage(BaseMessage):
        action: Literal["extra_event"] = "extra_event"
        payload: str


    class ExtraEventHandlerMixin:
        @event_handler(
            summary="Handle extra event",
            description="Simple extra event message",
        )
        async def handle_extra_event(
            self, event: ExtraEventMessage
        ) -> ExtraResponseMessage:
            return ExtraResponseMessage(payload=event.payload + " any extra thing")

Compose into a consumer:

.. code-block:: python

    class BackgroundJobConsumer(ExtraEventHandlerMixin, AsyncJsonWebsocketConsumer):
        @ws_handler(summary="Handle job requests")
        async def handle_job(self, message: JobMessage) -> None:
            ...

Combining Multiple Mixins
--------------------------

A single consumer can use multiple mixins:

.. code-block:: python

    class FullFeaturedConsumer(
        ExtraWsHandlerMixin,
        ExtraEventHandlerMixin,
        AsyncJsonWebsocketConsumer,
    ):
        @ws_handler(summary="Handle ping")
        async def handle_ping(self, _message: PingMessage) -> PongMessage:
            return PongMessage()

This consumer handles ``ping``, ``extra_request`` (from the WebSocket mixin), and ``extra_event`` (from the event mixin).

How It Works
------------

Mixin handlers are auto-discovered through Python's method resolution order (MRO). When a consumer class is defined, Chanx scans all methods in the inheritance chain for ``@ws_handler`` and ``@event_handler`` decorators and registers them in the consumer's handler maps. This means:

- **No extra registration** — just add the mixin to your class's bases
- **Message routing works automatically** — mixin handlers are routed the same way as handlers defined directly on the consumer
- **AsyncAPI docs include mixin handlers** — generated documentation reflects all handlers, including those from mixins
