Topics
======

A topic is a subscribable stream on a consumer's connection. Mounting several topics on one consumer lets a single WebSocket serve many resources, with each topic keeping its own handlers, its own authorization and its own channel group.

This is the same shape as Phoenix Channels' topics or Centrifugo's channels: one connection, many named streams, addressed per frame.

Defining a topic
----------------

A topic is a pattern plus handlers plus an ``authorize`` hook:

.. code-block:: python

    from chanx.core.decorators import event_handler, ws_handler
    from chanx.core.topic import Topic


    class DiscussionTopic(Topic):
        pattern = "discussion:{pk}"

        async def authorize(self, pk: str) -> bool:
            return await user_can_view(self.scope["user"], pk)

        @ws_handler
        async def handle_reply(self, message: ReplyMessage) -> ReplyCreatedMessage:
            return ReplyCreatedMessage(payload=message.payload)

        @event_handler
        async def handle_new_reply(self, event: NewReplyEvent) -> ReplyCreatedMessage:
            return ReplyCreatedMessage(payload=event.payload)

Handlers are written exactly as they are on a consumer. ``self.params`` holds the values parsed from the pattern.

A topic resolves its own channel layer, so importing it from ``chanx.core.topic`` keeps it framework-agnostic - the same class can be mounted on a Channels consumer or a fast-channels one. ``Topic.as_consumer()`` resolves the framework's consumer base the same way, so a topic can be mounted on a route without importing either integration.

Mounting topics on a consumer
-----------------------------

.. code-block:: python

    from chanx.channels.websocket import AsyncJsonWebsocketConsumer


    class HubConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = JWTAuthenticator      # authenticates the socket once
        topics = [DiscussionTopic, RoomTopic]

        @ws_handler
        async def handle_ping(self, _message: PingMessage) -> PongMessage:
            return PongMessage()

Because handlers are scoped per topic, two topics may both define an action such as ``cancel`` without conflicting. Frames that name no topic are handled by the consumer itself.

The wire protocol
-----------------

Routing metadata travels flat, alongside the message, so ``action`` remains the top-level discriminator:

.. code-block:: text

    -> {"version": 1, "topic": "discussion:5", "ref": "1", "action": "subscribe"}
    <- {"version": 1, "topic": "discussion:5", "ref": "1", "action": "subscribed"}
    -> {"version": 1, "topic": "discussion:5", "ref": "2", "action": "reply", "payload": {...}}
    <- {"version": 1, "topic": "discussion:5", "ref": "2", "action": "reply_created", "payload": {...}}
    <- {"version": 1, "topic": "discussion:5", "seq": 142, "action": "new_reply", "payload": {...}}
    -> {"version": 1, "ref": "3", "action": "ping"}          # no topic: the consumer's own handlers

===========  ===========================================================
Field        Meaning
===========  ===========================================================
``version``  Envelope version, so the format can change later
``topic``    Which stream the frame belongs to; absent for the consumer
``ref``      Correlates a reply with its request; absent on server push
``seq``      Optional, producer-assigned, for gap detection only
===========  ===========================================================

Subscribing
-----------

``subscribe`` matches the topic against the mounted patterns, runs ``authorize`` and joins the topic's channel group. The reply carries the request's ``ref``, so a denial is correlated with the attempt rather than arriving as a stray error. ``unsubscribe`` leaves the group, and disconnecting leaves every subscribed group.

Topic strings are mapped to channel layer group names, because channel layers only accept alphanumerics, hyphens, underscores and periods - so ``discussion:5`` is joined as ``DiscussionTopic.discussion_5``. Backends also cap group names at 100 characters, so a long topic is truncated with a digest suffix that keeps it deterministic and distinct.

Subscription lifecycle
----------------------

A topic that keeps state per subscriber - a presence roster, a chat backlog - hooks the moment a client joins or leaves:

.. code-block:: python

    class PresenceTopic(Topic):
        pattern = "presence:{room}"

        async def on_subscribe(self) -> None:
            """Runs once the group is joined. Send whatever state the client needs."""
            await self.send_message(await self.roster())

        async def on_unsubscribe(self) -> None:
            """Runs on unsubscribe *and* on disconnect, so cleanup happens once."""
            await self.announce_departure()

``on_subscribe`` runs after the group is joined, with the request's ``ref`` cleared - state it pushes is server-initiated, not a reply, so a client waiting on the subscribe request is not confused by it. ``on_unsubscribe`` runs before the group is left, on both an explicit ``unsubscribe`` and a disconnect.

Errors
------

A topic-level failure comes back as an ``error`` on that topic, carrying a machine-readable ``reason`` alongside the human-readable detail, so a client can branch without parsing prose:

===================  ==============================================
``reason``           Meaning
===================  ==============================================
``unknown_topic``    No mounted pattern matches the topic
``unauthorized``     ``authorize`` refused the subscription
``not_subscribed``   The frame addressed a topic not subscribed to
===================  ==============================================

Publishing
----------

Producers address a topic, not a connection:

.. code-block:: python

    await DiscussionTopic.broadcast(
        "discussion:5", NewReplyEvent(payload="hi"), seq=142
    )

The topic is stamped on the event, which is what lets a receiving consumer route it back to the right topic. ``seq`` is optional and assigned by the caller: a single producer can number its own frames without coordination, while a topic with several writers should leave it unset. It supports gap detection only - there is no replay, so a client that sees a gap should resync from a normal endpoint.

Serving one topic on its own route
----------------------------------

The same class can also back a dedicated route, where connecting *is* the subscription and clients need no envelope:

.. code-block:: python

    path("ws/discussion/<int:pk>/", DiscussionTopic.as_consumer().as_asgi())

The URL parameters fill the pattern, so ``/ws/discussion/5/`` subscribes ``discussion:5`` - the same group the multiplexed route uses. This means a topic can be exposed both ways at once, and existing clients on the dedicated route are unaffected.

Testing
-------

The test communicator addresses topics directly:

.. code-block:: python

    await comm.subscribe("discussion:5")
    await comm.send_message(ReplyMessage(payload="hi"), topic="discussion:5", ref="2")
    message = await comm.receive_topic_message(DiscussionTopic)
    await comm.unsubscribe("discussion:5")

``subscribe`` and ``unsubscribe`` return the reply frame, and ``receive_topic_message`` validates the frame against that topic's own messages.

AsyncAPI and generated clients
------------------------------

Topics share their route's address, so each is documented as its own channel at that address, carrying an ``x-topic`` extension with its pattern and parameters. This mirrors how AsyncAPI's own WebSocket examples describe several logical channels on one connection.

The generated client follows the same structure: one client owning the connection, handing out typed handles.

.. code-block:: python

    client = HubClient("localhost:8000")
    discussion = client.discussion_topic(pk=5)

    await discussion.subscribe()
    await discussion.send_message(ReplyMessage(payload="hi"))

The connection routes inbound frames to the right handle by topic, and matches replies to requests by ``ref``. After a reconnect, ``await client.resubscribe()`` restores every handle's subscription.
