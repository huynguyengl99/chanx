Ecosystem
=========

Chanx is the server. Two companion projects build on the AsyncAPI schema it generates.

chanx-js: JavaScript and TypeScript clients
-------------------------------------------

`chanx-js <https://huynguyengl99.github.io/chanx-js/>`_ is the client for browsers and
Node. ``@chanx-js/codegen`` turns your server's AsyncAPI schema into typed channel
descriptors, and ``@chanx-js/client`` connects with them, with bindings for React, Vue,
Svelte and Solid.

.. code-block:: bash

    pnpm add @chanx-js/client
    pnpm add -D @chanx-js/codegen
    npx @chanx-js/codegen http://localhost:8000/asyncapi.json -o src/generated

.. code-block:: tsx

    import { useChannel, useTopic } from '@chanx-js/client/react';

    import { chat, topicHub } from './generated';

    function ChatRoom({ room }: { room: string }) {
      const { lastMessage, send } = useChannel(chat, { params: { room } });
      const lobby = useTopic(topicHub, topicHub.topics.roomTopic.with({ room_name: room }));
      // Messages, params and topics are all typed from the schema.
    }

It speaks Chanx's wire protocol directly: the envelope, replies matched to requests by
``ref``, topic subscriptions that resume after a reconnect, and one shared socket for a
channel's topics. Requests on plain channels need Chanx 2.11.2 or later.

For a Python client, use the built-in :doc:`user-guide/client-generator`.

chanx-kit: copy-in components
-----------------------------

`chanx-kit <https://huynguyengl99.github.io/chanx-kit/>`_ is a registry of ready-made
WebSocket components built on Chanx: AG-UI agents, presence, room chat, notifications and
more. Kits are copied into your project with `copit <https://github.com/huynguyengl99/copit>`_,
so the code is yours to read and change.

.. code-block:: bash

    uvx copit registry add chanx-kit github:huynguyengl99/chanx-kit@v0.1.0 --to app/ws_kits
    uvx copit add @chanx-kit/notification
