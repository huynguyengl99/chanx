Multiplexing protocol
=====================

This page is the normative wire contract for a multiplexed route. :doc:`multiplexing` shows how to build one; this page is what a client has to implement to talk to it, and what Chanx promises not to break.

Everything here is written from the client's side of the socket. ``->`` is client to server, ``<-`` is server to client.

.. contents::
    :local:
    :depth: 1

Envelope
--------

A frame addressed to one sub-consumer is a JSON object with three fields:

.. code-block:: text

    -> {"version": 1, "consumer": "chat", "message": {"action": "chat", "payload": {...}}}
    <- {"version": 1, "consumer": "chat", "message": {"action": "chat_notification", "payload": {...}}}

``consumer``
    The envelope key naming the sub-consumer, as declared in the demultiplexer's ``consumers`` mapping. Arbitrary strings, independent of class names.

``message``
    The inner message, exactly what the consumer would send or receive on a route of its own.

``version``
    The envelope version. See `Versioning`_.

A frame **without** the ``consumer`` field is not an envelope: it belongs to the demultiplexer itself, and is a plain Chanx message.

.. code-block:: text

    -> {"action": "ping", "payload": null}
    <- {"action": "pong", "payload": null}

That distinction is the whole routing rule, in both directions. Anything the demultiplexer sends on its own behalf — the handshake, its errors, replies from its own handlers — is unwrapped. Anything a sub-consumer sends is enveloped.

The three field names are configurable per demultiplexer (``envelope_consumer_field``, ``envelope_message_field``, ``envelope_version_field``); a generated client reads them from the ``x-chanx-multiplex`` extension in the AsyncAPI document rather than assuming the defaults. Every channel of a multiplexed route carries that extension; the one without a ``consumerKey`` is the demultiplexer's own.

Everything on this page is implemented for you by the clients :doc:`client-generator` produces. Read it if you are writing a client by hand, or in another language.

Versioning
----------

The server stamps ``version`` on every envelope it sends. Incoming envelopes are checked leniently:

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Client sends
      - Server behaviour
    * - ``"version": 1``
      - Accepted and routed.
    * - No ``version`` field
      - Accepted and routed, taken to mean the version the route speaks.
    * - Any other value
      - Rejected with an unwrapped error naming the supported version. The frame is **not** routed; the socket stays open.

.. code-block:: text

    -> {"version": 2, "consumer": "chat", "message": {...}}
    <- {"action": "error", "payload": {"detail": "Unsupported envelope version 2", "version": 1}}

Two forward-compatibility rules clients must follow:

- **Ignore unknown top-level envelope fields.** A future version may add them.
- **Ignore unknown actions**, both at the top level and inside an envelope, rather than treating them as errors.

Camelization
------------

**Envelope fields are never camelized, in either direction.** Only the inner message follows its own sub-consumer's ``camelize`` setting, and the demultiplexer's own messages follow the demultiplexer's.

.. code-block:: text

    <- {"version": 1, "consumer": "chat", "message": {"action": "chat", "payload": {"roomName": "lobby"}}}
        └─ always as declared ─┘          └─ camelized per that consumer's setting ─┘

The reason is mechanical: the demultiplexer reads the envelope off the raw frame before any decamelization, and writes it after the sub-consumer has already serialized the inner message. Keep custom envelope field names single words anyway — it costs nothing and removes the question.

Connection lifecycle
--------------------

.. code-block:: text

    1. Client opens the socket.
    2. Demultiplexer accepts and runs its own authenticator.
         - denied  -> unwrapped authentication message, socket closed. Stop.
    3. Every sub-consumer connects and runs its own authenticator, in parallel.
         - each reports its own result under its own envelope key
         - a denied sub-consumer produces an unwrapped isolation error
    4. Demultiplexer sends multiplex_ready. The connection is now open for business.

.. code-block:: text

    <- {"action": "multiplex_ready",
        "payload": {"version": 1, "ready": ["chat", "notifications"], "unavailable": ["admin"]}}

``multiplex_ready`` is sent exactly once per connection, and is the **authoritative** statement of what the route serves:

- ``ready`` — keys that are connected, subscribed to their groups, and accepting messages.
- ``unavailable`` — keys that failed to connect. Addressing them returns an error.

A client may send before the handshake arrives, but has no guarantee about group traffic until then: a sub-consumer joins its groups during connect, so a broadcast issued earlier can be missed. **Wait for** ``multiplex_ready`` **before sending anything that expects a group reply.**

Per-stream state
----------------

Each envelope key is a *stream*. Streams are independent; one failing does not affect another.

.. list-table::
    :header-rows: 1
    :widths: 18 40 42

    * - State
      - Entered when
      - Client may
    * - ``pending``
      - The socket opened.
      - Send, but expect no group traffic yet.
    * - ``open``
      - The key appeared in ``multiplex_ready.ready``.
      - Send and receive freely.
    * - ``closed``
      - The key appeared in ``unavailable``, or an unwrapped ``Consumer '<key>' closed the connection`` error arrived.
      - Nothing. Stop sending to this key.

``closed`` is **terminal for the lifetime of the socket**. There is no per-stream reopen: a sub-consumer is started once, when the connection is established. The only way back is a new connection.

Reconnect
---------

**The socket is the unit of reconnect.** There is no per-stream reconnect, and no server-side per-stream state survives a drop — a reconnect starts every sub-consumer from scratch.

What comes back on its own:

- Group membership. Each sub-consumer re-runs its connect and re-joins its ``groups``.
- Authentication, both the shared one and each sub-consumer's.

What does **not** come back:

- Anything the client established by sending messages: room joins, subscriptions, filters, cursors, in-flight requests. The server has no record that you asked.

So a client should:

1. Back off and retry **the socket**, not individual streams. Exponential backoff with jitter; a stream that is ``unavailable`` is not a reason to reconnect faster.
2. On each connection, wait for ``multiplex_ready``.
3. Replay its per-key setup for every key in ``ready`` (see `Resubscription`_).
4. Treat everything in ``unavailable`` as unusable until the *next* reconnect.
5. Fail in-flight requests locally. Nothing is redelivered, and message ids are not stable across connections.

Resubscription
--------------

Keep the setup a stream needs as data, per key, rather than as a sequence of calls made once at startup:

.. code-block:: python

    subscriptions = {
        "chat": [JoinRoomMessage(payload={"room": "lobby"})],
        "notifications": [SubscribeMessage(payload={"topics": ["billing"]})],
    }

    async def on_ready(ready: list[str], unavailable: list[str]) -> None:
        for key in ready:
            for message in subscriptions.get(key, []):
                await send(key, message)

Because that runs on every ``multiplex_ready``, the first connection and every reconnect take the same path — which is the only way the reconnect path stays tested.

Two rules worth stating:

- Resubscribe **per key**, never globally. Keys succeed and fail independently, and a key in ``unavailable`` must be skipped rather than retried.
- Make the setup messages idempotent. A reconnect the client did not notice will replay them.

Authentication denial
---------------------

The demultiplexer authenticates the shared connection once. Sub-consumers still run their own authenticators, because a sub-consumer may require more than the shared connection does.

If the **demultiplexer's** authenticator denies, the socket is closed. Nothing is multiplexed.

If a **sub-consumer's** authenticator denies, only that key is affected. The client sees two things:

.. code-block:: text

    <- {"action": "error", "payload": {"detail": "Consumer 'admin' closed the connection", "consumer": "admin"}}
    <- {"action": "multiplex_ready", "payload": {"version": 1, "ready": ["chat"], "unavailable": ["admin"]}}

The isolation error is per-key and easy to miss in a burst; the handshake is the one frame that always describes the whole route. **Drive UI state off** ``multiplex_ready``, and treat the isolation error as a notification.

The client must not retry the denied key on the same socket — every later frame addressed to it gets an error, and the sub-consumer is not restarted. If the denial is recoverable (an expired token, say), refresh the credential and open a new connection.

Errors
------

Whether an error is enveloped tells the client whose problem it is.

.. list-table::
    :header-rows: 1
    :widths: 22 38 40

    * - Shape
      - Cause
      - Client action
    * - Unwrapped
      - Unknown or unavailable consumer key
      - Bug or stale state; stop addressing that key.
    * - Unwrapped
      - Malformed envelope (missing ``consumer`` or ``message``, wrong types)
      - Bug in the client's framing.
    * - Unwrapped
      - Unsupported envelope version
      - Client and server disagree on the protocol; upgrade one of them.
    * - Unwrapped
      - Raised by one of the demultiplexer's own handlers
      - Handle like any single-consumer error.
    * - Enveloped
      - Raised by the named sub-consumer: validation, an unknown action, a handler failure
      - Scope the failure to that stream; the rest of the route is fine.

Every error carries ``payload.detail``. Errors about a specific key also carry the key under the envelope's consumer field name.

Delivery guarantees
-------------------

**Ordering is not guaranteed** — not across streams, and not within one. Chanx handles each incoming message in its own task, on a multiplexed route exactly as on a dedicated one, so two messages sent back to back may be answered out of order. A client that needs to correlate a reply with a request must carry its own correlation id in the payload.

**Completion is per stream.** Each sub-consumer sends its own ``complete`` / ``group_complete`` / ``event_complete``, enveloped under its key. A client waiting for "the" completion of a request must match both the key and the action.

**Text frames only.** Binary frames are not multiplexed; a sub-consumer that tries to send one has that frame dropped and logged server-side.

**Nesting is not supported.** A demultiplexer cannot serve another demultiplexer, so an envelope is never nested inside an envelope.

Server-side contract
--------------------

One internal contract is worth knowing, because it is what makes the handshake trustworthy: a Chanx consumer invokes the zero-argument callable at ``scope["chanx_connect_complete"]``, if present, exactly once when its ``websocket_connect`` finishes — after groups are joined, and also when authentication denied the request or an exception is propagating.

The demultiplexer puts that callable in each sub-consumer's scope and waits on it before sending ``multiplex_ready``. Consumers on a route of their own never carry the key and are unaffected. Nothing about a sub-consumer has to change to be multiplexed.
