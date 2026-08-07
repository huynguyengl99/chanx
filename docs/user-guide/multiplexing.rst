Multiplexing
============

A single WebSocket route normally serves a single consumer, so a frontend that needs several consumers has to open several connections. Browsers cap how many connections a page may hold open to one host, and even below the cap each connection carries its own reconnect, backoff and authentication lifecycle to manage.

A **demultiplexer** serves many consumers over one connection. Each frame carries a small envelope naming the target consumer, and the demultiplexer routes it there; frames a consumer sends back are enveloped on the way out.

.. code-block:: text

    -> {"version": 1, "consumer": "chat",   "message": {"action": "chat", "payload": {"message": "hi"}}}
    <- {"version": 1, "consumer": "chat",   "message": {"action": "chat_notification", "payload": {...}}}
    -> {"version": 1, "consumer": "system", "message": {"action": "ping", "payload": null}}
    <- {"version": 1, "consumer": "system", "message": {"action": "pong", "payload": null}}

This page is the how-to. :doc:`multiplex-protocol` is the wire contract a client implements against — envelope, versioning, reconnect and per-stream state.

Declaring a demultiplexer
-------------------------

Import the demultiplexer for your framework and map wire keys to consumer classes. Keys are arbitrary strings, independent of the class names, and are what the client puts in the envelope.

**Django Channels:**

.. code-block:: python

    from chanx.channels.multiplex import AsyncJsonWebsocketDemultiplexer


    class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
        consumers = {
            "chat": ChatConsumer,
            "notifications": NotificationConsumer,
        }

**FastAPI:**

.. code-block:: python

    from chanx.fast_channels.multiplex import AsyncJsonWebsocketDemultiplexer


    class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
        consumers = {
            "chat": ChatConsumer,
            "notifications": NotificationConsumer,
        }

Mount it like any other consumer — with ``chanx.channels.routing.path`` on Django:

.. code-block:: python

    from channels.routing import URLRouter

    from chanx.channels.routing import path

    router = URLRouter([path("mux/", MainDemultiplexer.as_asgi())])

or as a WebSocket route on FastAPI:

.. code-block:: python

    ws_router.add_websocket_route("/mux", MainDemultiplexer.as_asgi())

Sub-consumers need no changes at all. The same consumer class can serve a dedicated route and be multiplexed at the same time.

Knowing when the route is open
------------------------------

Once every sub-consumer has finished connecting — groups joined included — the demultiplexer sends a single unwrapped handshake:

.. code-block:: text

    <- {"action": "multiplex_ready",
        "payload": {"version": 1, "ready": ["chat", "notifications"], "unavailable": []}}

``ready`` lists the keys a client may address; ``unavailable`` lists those that failed to connect, most often because their own authenticator denied the request. A client that waits for this frame before sending cannot race ahead of the sub-consumers joining their groups.

Readiness is not guesswork on the demultiplexer's part: the Chanx base consumer invokes a callback the demultiplexer puts in each sub-consumer's scope under ``chanx_connect_complete``, once, when ``websocket_connect`` returns. Consumers on their own route never carry the key. See :doc:`multiplex-protocol` for the full contract.

What sub-consumers keep
-----------------------

Each sub-consumer runs as a real consumer driven through the ASGI protocol, with its own channel name and its own channel layer subscription. Everything therefore behaves exactly as it does on a dedicated route:

- ``groups`` are joined and discarded as usual
- ``broadcast_message()`` reaches every member of the group, on multiplexed and dedicated routes alike
- ``broadcast_event()`` / ``send_event()`` and ``@event_handler`` work unchanged
- ``camelize``, ``send_completion``, logging and error handling follow each sub-consumer's own settings

Completion and error messages are enveloped under the consumer that produced them, so a client can tell whose request finished.

Top-level handlers
------------------

The demultiplexer is itself a full Chanx consumer. A frame that arrives **without** the envelope field is handled by the demultiplexer's own ``@ws_handler`` methods, which is how you keep a single shared action such as a ping:

.. code-block:: python

    class MainDemultiplexer(AsyncJsonWebsocketDemultiplexer):
        consumers = {"chat": ChatConsumer}

        @ws_handler
        async def handle_ping(self, _message: PingMessage) -> PongMessage:
            return PongMessage()

.. code-block:: text

    -> {"action": "ping", "payload": null}
    <- {"action": "pong", "payload": null}

Messages the demultiplexer itself sends are never enveloped. That includes its errors, which is how a client distinguishes a transport-level problem from a reply by one of the sub-consumers.

Authentication
--------------

Set ``authenticator_class`` on the demultiplexer to authenticate the shared connection once. If it denies the request, the connection is closed and no sub-consumer is started.

Sub-consumers still run their own authenticators afterwards, because a sub-consumer may require more than the shared connection does. Each reports its own authentication result under its own envelope key.

Isolating a failed sub-consumer
-------------------------------

If a sub-consumer closes the connection — most often because its own authenticator denied the request — only that key is affected. The shared socket and every other sub-consumer keep running, and the client is told with an unwrapped error:

.. code-block:: text

    <- {"action": "error", "payload": {"detail": "Consumer 'admin' closed the connection",
                                       "consumer": "admin"}}

Later frames addressed to that key get an error rather than being silently dropped. Addressing a key the demultiplexer does not serve behaves the same way.

Configuration
-------------

.. list-table::
    :header-rows: 1
    :widths: 30 20 50

    * - Attribute
      - Default
      - Description
    * - ``consumers``
      - ``{}``
      - Mapping of wire key to consumer class.
    * - ``envelope_consumer_field``
      - ``"consumer"``
      - Envelope field naming the target consumer.
    * - ``envelope_message_field``
      - ``"message"``
      - Envelope field holding the inner message.
    * - ``envelope_version_field``
      - ``"version"``
      - Envelope field carrying the protocol version.
    * - ``envelope_version``
      - ``1``
      - Version stamped on outgoing envelopes and required of incoming ones that declare a version.
    * - ``child_connect_timeout``
      - ``5.0``
      - Seconds to wait for sub-consumers to finish connecting before routing traffic.
    * - ``child_shutdown_timeout``
      - ``5.0``
      - Seconds to wait for sub-consumers to shut down cleanly on disconnect.

To match an existing client protocol, rename the envelope fields:

.. code-block:: python

    class StreamDemultiplexer(AsyncJsonWebsocketDemultiplexer):
        consumers = {"chat": ChatConsumer}
        envelope_consumer_field = "stream"
        envelope_message_field = "data"
        envelope_version_field = "v"

.. code-block:: text

    -> {"v": 1, "stream": "chat", "data": {"action": "chat", "payload": {...}}}

Envelope field names are used verbatim on the wire in both directions: unlike the inner messages, the envelope is never camelized. Keeping custom names single words still saves confusion.

Testing
-------

Pass the demultiplexer as the communicator's ``consumer`` and the usual helpers become envelope-aware.

.. code-block:: python

    async with WebsocketCommunicator(app, "/ws/mux", consumer=MainDemultiplexer) as comm:
        # Address one sub-consumer
        await comm.send_message(ChatMessage(payload="hi"), consumer="chat")

        # Inner messages are validated against the consumer they came from
        assert await comm.receive_all_messages(stop_consumer="chat") == [
            ChatNotification(payload="hi")
        ]

        # Omit consumer= to reach the demultiplexer's own handlers
        await comm.send_message(PingMessage())

``receive_all_envelopes()`` returns ``(consumer_key, message)`` pairs when you need to know who sent what; the key is ``None`` for messages the demultiplexer sent itself.

Every sub-consumer sends its own completion message, so a bare ``stop_action`` stops at whichever arrives first. Pass ``stop_consumer`` to wait for a particular sub-consumer's completion instead.

The collecting helpers skip the ``multiplex_ready`` handshake, so tests that do not care about it need no changes. ``receive_multiplex_ready()`` returns it when you do — either to assert on it, or as the point where the sub-consumers are known to have joined their groups:

.. code-block:: python

    ready = await comm.receive_multiplex_ready()
    assert ready.payload.unavailable == []

    # Group traffic broadcast from here on is guaranteed to reach the sub-consumers.
    await ChatConsumer.broadcast_event(NewMessageEvent(...), groups=["room_1"])

AsyncAPI documentation
----------------------

A multiplexed route is documented as one channel per sub-consumer, all sharing the route's address and named ``<demultiplexer>_<key>``. Each carries an ``x-chanx-multiplex`` extension describing how to address it:

.. code-block:: json

    {
      "address": "/ws/mux",
      "x-chanx-multiplex": {
        "consumerField": "consumer",
        "messageField": "message",
        "versionField": "version",
        "version": 1,
        "consumerKey": "chat"
      }
    }

The demultiplexer also gets a channel of its own, carrying the ``multiplex_ready`` handshake and any top-level handlers it declares.

.. note::

    The message payloads in the specification describe the **inner** messages, not the envelope around them. :doc:`client-generator` reads the extension and builds the envelope for you: a multiplexed route generates one demultiplexer client owning the connection and one sub-client per consumer.

Limitations
-----------

- Demultiplexers cannot be nested inside one another.
- Only JSON text frames are multiplexed; a sub-consumer that sends binary data has that frame dropped and logged.
- Ordering across sub-consumers is not guaranteed. Chanx already handles each incoming message in its own task, so this matches single-consumer behaviour.
