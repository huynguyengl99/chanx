Comparison with Other Solutions
================================

Chanx vs Django Channels
-------------------------

Django Channels is the foundation that Chanx builds upon for Django projects. **Chanx is an extension, not a replacement**—it adds batteries-included features on top of Channels.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Django Channels
     - Chanx
   * - **Message Routing**
     - Manual if-else chains
     - Automatic via ``@ws_handler`` decorators
   * - **Type Safety**
     - Raw dicts, no static checking
     - Full mypy/pyright + Pydantic validation
   * - **Validation**
     - Manual, per-handler
     - Automatic with Pydantic models
   * - **AsyncAPI Docs**
     - None
     - Auto-generated from decorators
   * - **Testing**
     - Basic ``WebsocketCommunicator``
     - Enhanced with ``receive_all_messages()``, test cases
   * - **Authentication**
     - Build yourself
     - Built-in ``DjangoAuthenticator`` + DRF support
   * - **Logging**
     - Basic
     - Structured with ``structlog``, auto tracing
   * - **Channel Layers**
     - ✅ Yes
     - ✅ Yes (uses Channels' layers)
   * - **Broadcasting**
     - Manual setup
     - Type-safe ``broadcast_message()``

**Code Comparison**

.. code-block:: python

    # Django Channels - Manual routing
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        if action == "chat":
            await self.handle_chat(data)
        elif action == "ping":
            await self.handle_ping(data)
        # ... endless if-else chains

    # Chanx - Automatic routing
    @ws_handler
    async def handle_chat(self, message: ChatMessage) -> None:
        await self.broadcast_message(...)

    @ws_handler
    async def handle_ping(self, message: PingMessage) -> PongMessage:
        return PongMessage()

**What Django Channels Lacks**

Django Channels provides the infrastructure, but leaves critical features to you:

- **No message routing** - Write if-else chains for every action
- **No validation** - Manually parse and validate each message
- **No type safety** - Raw dicts everywhere, runtime errors are common
- **No API documentation** - Frontend teams ask "what messages can I send?"
- **Basic testing** - Manual test setup, no ``receive_all_messages()`` helper
- **No authentication helpers** - Build auth and permissions from scratch
- **No structured logging** - Basic logging, hard to trace message flows

**When to Use Plain Django Channels**

- Absolute minimal overhead (performance-critical, every millisecond matters)
- Extremely simple use case (1-2 message types, never growing)
- Integrating with legacy code that can't be refactored

**Our Take**: Even for simple cases, Chanx's type safety and automatic routing prevent bugs and save development time. The performance overhead is negligible (~1-2ms for Pydantic validation).

Chanx vs Broadcaster (FastAPI)
-------------------------------

Broadcaster is a minimal pub/sub library (~300 lines) for broadcasting messages across server instances. Chanx is a full-featured WebSocket framework.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Broadcaster
     - Chanx
   * - **Scope**
     - Pub/sub only
     - ✅ Full WebSocket framework
   * - **Message Routing**
     - ❌ Manual if-else chains
     - ✅ Automatic via decorators
   * - **Validation**
     - ❌ Manual
     - ✅ Automatic Pydantic
   * - **Type Safety**
     - ❌ Raw bytes/strings
     - ✅ End-to-end with Pydantic
   * - **AsyncAPI Docs**
     - ❌ None
     - ✅ Auto-generated
   * - **Testing**
     - ❌ DIY with TestClient
     - ✅ ``WebsocketCommunicator`` + full test suite
   * - **Authentication**
     - ❌ Manual
     - ✅ Built-in with DRF permissions
   * - **Group Management**
     - ❌ Manual channel subscriptions
     - ✅ Automatic groups, declarative
   * - **Connection Tracking**
     - ❌ Manual
     - ✅ Automatic
   * - **Structured Logging**
     - ❌ None
     - ✅ Built-in with structlog, auto tracing
   * - **Binary Data**
     - ✅ Yes
     - ✅ Yes (via Pydantic models)
   * - **Event Broadcasting**
     - ❌ None
     - ✅ From anywhere (views, tasks, scripts)
   * - **Channel Layers**
     - Basic pub/sub
     - ✅ Redis, in-memory (via Channels)
   * - **Dependencies**
     - Minimal
     - channels/fast-channels

**Code Comparison**

.. code-block:: python

    # Broadcaster - Manual routing
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        async with broadcaster.subscribe(channel="chatroom") as subscriber:
            async for event in subscriber:
                data = json.loads(event.message)
                action = data.get("action")
                if action == "chat":
                    # Manual handling, validation, etc.
                    pass

    # Chanx - Automatic routing
    @channel(name="chat")
    class ChatConsumer(AsyncJsonWebsocketConsumer):
        @ws_handler
        async def handle_chat(self, message: ChatMessage) -> None:
            await self.broadcast_message(...)

**What Broadcaster Lacks**

Broadcaster only handles pub/sub messaging. You still need to manually build:

- Message routing (write if-else chains for every action)
- Validation (parse and validate every message yourself)
- Type safety (no mypy/pyright support)
- Documentation (no API docs for frontend)
- Testing utilities (write custom test helpers)
- Authentication (implement auth flow manually)
- Connection tracking (maintain active connections yourself)

**When to Choose Broadcaster**

- Only need basic pub/sub (not WebSocket connection management)
- Extremely simple use case (1-2 message types, no growth expected)

**When to Choose Chanx**

- Building a real WebSocket application with multiple message types
- Want to avoid reinventing routing, validation, and testing
- Need type safety to catch bugs during development
- Want automatic API documentation for frontend teams
- Need authentication and permissions
- Working in a team where consistent patterns matter

**Reality Check**: Nearly every project that starts with Broadcaster ends up building routing, validation, testing, and documentation on top. Chanx gives you these from day one, saving weeks of development.

Chanx vs Socket.IO
-------------------

Socket.IO is a mature WebSocket library (since 2010) built primarily for Node.js. While python-socketio exists, it's challenging to integrate with Django or FastAPI.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Socket.IO (python-socketio)
     - Chanx
   * - **Framework Integration**
     - ⚠️ Requires custom ASGI/WSGI adapters, separate from Django/FastAPI routing
     - ✅ Native Django Channels and FastAPI integration
   * - **Django Integration**
     - ⚠️ Bypasses Django routing, ORM access is manual
     - ✅ Native (ORM, auth, permissions, middleware)
   * - **FastAPI Integration**
     - ⚠️ Separate ASGI app, can't use FastAPI dependencies/middleware
     - ✅ Native, uses FastAPI routing and dependencies
   * - **Type Safety**
     - ❌ Runtime only, no static checking
     - ✅ Full mypy/pyright + Pydantic validation
   * - **AsyncAPI Docs**
     - ❌ Manual
     - ✅ Auto-generated
   * - **Client Libraries**
     - ✅ Official for JS, iOS, Android, Java, C++
     - ⚠️ Standard WebSocket (available everywhere, less tooling)
   * - **Fallback Protocols**
     - ✅ Long-polling for old browsers (rarely needed in 2025)
     - ❌ WebSocket only
   * - **Binary Data**
     - ✅ First-class
     - ⚠️ JSON-focused
   * - **Ecosystem**
     - ✅ Node.js: mature | Python: port
     - ✅ Native Python
   * - **Primary Use Case**
     - Node.js apps, cross-platform clients
     - Python/Django/FastAPI apps

**What's Missing from Socket.IO in Python**

python-socketio is a port of the Node.js library and presents several challenges:

- **Framework isolation** - Runs as a separate ASGI/WSGI app, bypasses Django/FastAPI routing
- **No middleware integration** - Can't use Django middleware or FastAPI dependencies
- **Duplicate auth** - Must reimplement authentication separately from Django/DRF or FastAPI
- **Pattern mismatch** - Node.js-style event emitters feel unnatural with Python async/await
- **No type safety** - Runtime-only checks, no mypy/pyright support
- **No AsyncAPI docs** - Manual documentation only
- **Separate testing** - Can't use Django TestCase or FastAPI TestClient naturally

**When Socket.IO Makes Sense**

- Legacy frontend already using Socket.IO client
- Need official mobile SDKs with auto-reconnection built-in
- **Building with Node.js** (Socket.IO's native environment)

**When to Choose Chanx**

- Python backend (Django/FastAPI)
- Want native framework integration (routing, auth, middleware just work)
- Need type safety to catch bugs during development
- Want automatic API documentation
- Modern browsers (WebSocket support universal since 2017)
- Prefer idiomatic Python patterns

Overall Feature Comparison
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15 15

   * - Feature
     - Chanx
     - Channels
     - Broadcaster
     - Socket.IO
   * - **Automatic Routing**
     - ✅ Yes
     - ❌ Manual
     - ❌ Manual
     - ✅ Yes
   * - **Static Type Safety**
     - ✅ Full
     - ❌ None
     - ❌ None
     - ❌ Runtime only
   * - **Automatic Validation**
     - ✅ Pydantic
     - ❌ Manual
     - ❌ Manual
     - ❌ Manual
   * - **AsyncAPI Docs**
     - ✅ Auto
     - ❌ None
     - ❌ None
     - ❌ Manual
   * - **Testing Utilities**
     - ✅ Full
     - ⚠️ Basic
     - ❌ None
     - ⚠️ Own tools
   * - **Authentication**
     - ✅ Built-in
     - ❌ Manual
     - ❌ Manual
     - ⚠️ Separate
   * - **Group Broadcasting**
     - ✅ Yes
     - ✅ Yes
     - ⚠️ Manual
     - ✅ Rooms
   * - **Event Broadcasting**
     - ✅ From views/tasks/scripts
     - ⚠️ Manual setup
     - ❌ None
     - ⚠️ Manual setup
   * - **Django Integration**
     - ✅ Native
     - ✅ Native
     - ❌ None
     - ⚠️ Separate app
   * - **FastAPI Integration**
     - ✅ Native
     - ⚠️ fast-channels
     - ✅ Native
     - ⚠️ Separate app
   * - **Python Ecosystem**
     - ✅ Native
     - ✅ Native
     - ✅ Native
     - ⚠️ Node.js port
   * - **Client Libraries**
     - ⚠️ Standard WS
     - ⚠️ Standard WS
     - ⚠️ Standard WS
     - ✅ Multi-platform
   * - **Binary Data**
     - ✅ Yes (Pydantic)
     - ✅ Yes
     - ✅ Yes
     - ✅ First-class
   * - **Structured Logging**
     - ✅ Built-in
     - ⚠️ Basic
     - ❌ None
     - ⚠️ Basic

Legend: ✅ Strong support | ⚠️ Partial/Manual | ❌ Not supported

Quick Recommendations
----------------------

**Choose Chanx** → Python/Django/FastAPI apps needing type safety, automatic docs, and faster development

**Choose Django Channels** → Absolute minimal overhead or legacy integration

**Choose Broadcaster** → Simple pub/sub only, minimal dependencies

**Choose Socket.IO** → Legacy projects already using Socket.IO, or Node.js backend

**Bottom Line**: For Python/Django/FastAPI, Chanx eliminates the boilerplate. You get automatic routing, type safety, validation, API docs, authentication, and testing utilities from day one—features you'd spend weeks building on top of other solutions.

Next Steps
----------

- :doc:`introduction` - Learn more about Chanx
- :doc:`quick-start-django` - Get started with Django
- :doc:`quick-start-fastapi` - Get started with FastAPI
