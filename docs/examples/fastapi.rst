FastAPI Complete Example
=========================

This example demonstrates a comprehensive WebSocket application using FastAPI and Chanx. The sandbox showcases modular app architecture, multiple channel layer types, real ARQ background job processing, and advanced WebSocket patterns across multiple consumer types.

Overview
--------

The FastAPI sandbox implements a sophisticated multi-consumer WebSocket system featuring:

- **Modular App Architecture** with 4 distinct consumer apps demonstrating different patterns
- **Multiple Channel Layer Types** (Memory, Redis Pub/Sub, Redis Queue) used strategically
- **Real ARQ Background Jobs** with job queuing and result streaming
- **Dynamic Room Management** with path parameter extraction
- **Direct WebSocket Communication** without channel layers for simple use cases
- **Interactive HTML/JS Client** with multiple chat interfaces
- **Production Development Setup** with coordinated FastAPI + ARQ worker startup

Quick Start
-----------

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/huynguyengl99/chanx
      cd chanx

2. **Prerequisites**: Ensure Docker and uv are installed
3. **Start services**: Run ``docker compose up -d`` to start Redis and PostgreSQL
4. **Install dependencies**: Run ``uv sync --all-extras``
5. **Activate virtual environment**:

   .. code-block:: bash

      source .venv/bin/activate

6. **Start the application**:

   .. code-block:: bash

      python sandbox_fastapi/start_dev.py

7. **Access the application**:

   - Main interface: http://localhost:8080/
   - AsyncAPI docs: http://localhost:8080/asyncapi
   - JSON spec: http://localhost:8080/asyncapi.json
   - YAML spec: http://localhost:8080/asyncapi.yaml

The development script starts both the FastAPI application and ARQ worker for background job processing.

Project Structure
-----------------

The FastAPI sandbox demonstrates clean modular architecture:

.. code-block::

   sandbox_fastapi/
   ├── main.py                  # FastAPI app with WebSocket routing + HTML client
   ├── start_dev.py            # Production development script (FastAPI + ARQ)
   ├── base_consumer.py        # Environment-based configuration for all consumers
   ├── layers.py               # Multi-type channel layer setup with fast-channels
   ├── tasks.py                # Real ARQ background tasks with result streaming
   ├── worker.py               # ARQ worker configuration
   ├── external_sender.py      # External event broadcasting examples
   ├── static/                 # CSS/JS for interactive HTML client
   └── apps/                   # Modular consumer architecture
       ├── showcase/           # 4 consumers showing different channel layer types
       │   ├── consumer.py     # Chat, Reliable, Notifications, Analytics
       │   └── messages.py     # Pydantic message definitions
       ├── room_chat/          # Dynamic room-based messaging
       │   ├── consumer.py     # Path parameter extraction + room groups
       │   └── messages.py     # Room-specific message types
       ├── background_jobs/    # Real ARQ integration
       │   ├── consumer.py     # Job queuing + result event handling
       │   └── messages.py     # Job processing message types
       └── system_chat/        # Direct WebSocket (no channel layers)
           ├── consumer.py     # Simple echo without groups
           └── messages.py     # Direct response messages

Key Consumer Applications
--------------------------

**1. System Chat App (apps/system_chat/consumer.py) - No Channel Layers:**

.. code-block:: python

   @channel(name="system", description="Direct WebSocket without channel layers")
   class SystemMessageConsumer(BaseConsumer):
       # No channel_layer_alias = direct WebSocket only

       @ws_handler
       async def handle_system(self, message: UserMessage) -> SystemEchoMessage:
           # Direct response without groups or broadcasting
           return SystemEchoMessage(payload=MessagePayload(
               message=f"🔧 System Echo: {message.payload.message}"
           ))

**2. Room Chat App (apps/room_chat/consumer.py) - Dynamic Path Parameters:**

.. code-block:: python

   @channel(name="room_chat", description="Dynamic room-based messaging")
   class RoomChatConsumer(BaseConsumer):
       channel_layer_alias = "chat"

       async def post_authentication(self) -> None:
           # Extract room from WebSocket path: /ws/room/{room_name}
           self.room_name = self.scope["path_params"]["room_name"]
           self.room_group_name = f"room_{self.room_name}"

           # Join room group dynamically
           await self.channel_layer.group_add(self.room_group_name, self.channel_name)
           self.groups.append(self.room_group_name)

**3. Background Jobs App (apps/background_jobs/consumer.py) - Real ARQ Integration:**

.. code-block:: python

   @channel(name="background_jobs", description="Real background job processing with ARQ")
   class BackgroundJobConsumer(BaseConsumer[JobResult]):
       channel_layer_alias = "chat"

       @ws_handler(output_type=JobStatusMessage)
       async def handle_job(self, message: JobMessage) -> None:
           # Queue real ARQ job
           job_id = await queue_job(
               message.payload.type,
               message.payload.content,
               self.channel_name
           )

           # Send immediate confirmation
           await self.send_message(JobStatusMessage(payload={
               "status": "queued",
               "job_id": job_id
           }))

       @event_handler
       async def handle_job_result(self, event: JobResult) -> JobStatusMessage:
           # Receive results from ARQ worker
           return JobStatusMessage(payload={"status": "result", "message": event.payload})

**4. Showcase App (apps/showcase/consumer.py) - 4 Different Channel Layer Types:**

.. code-block:: python

   # Chat Consumer - Redis Pub/Sub Layer
   @channel(name="chat", description="Basic Chat Consumer using centralized chat layer")
   class ChatConsumer(BaseConsumer[SystemNotify]):
       channel_layer_alias = "chat"  # Redis Pub/Sub for real-time
       groups = ["chat_room"]

       @ws_handler(output_type=ChatNotificationMessage)
       async def handle_chat(self, message: ChatMessage) -> None:
           await self.broadcast_message(
               ChatNotificationMessage(payload=ChatPayload(
                   message=f"💬 {message.payload.message}"
               ))
           )

   # Reliable Chat Consumer - Redis Queue Layer
   @channel(name="reliable_chat", description="Reliable Chat using queue-based layer")
   class ReliableChatConsumer(BaseConsumer[SystemNotify]):
       channel_layer_alias = "queue"  # Redis Queue for reliability
       groups = ["reliable_chat"]

   # Analytics Consumer - High-capacity Redis Layer
   @channel(name="analytics", description="Analytics events with reliable delivery")
   class AnalyticsConsumer(BaseConsumer[SystemNotify]):
       channel_layer_alias = "analytics"  # High-capacity Redis (5000 messages)
       groups = ["analytics"]

Channel Layer Configuration
---------------------------

**Strategic Multi-Layer Setup (sandbox_fastapi/layers.py):**

.. literalinclude:: ../../sandbox_fastapi/layers.py
   :language: python

**Layer Strategy Breakdown:**

- **Memory Layer**: Development/testing without Redis dependency
- **Chat Layer (Redis Pub/Sub)**: Real-time messaging with instant delivery
- **Queue Layer (Redis Queue)**: Reliable messaging with persistence (15min expiry, 1000 capacity)
- **Notifications Layer (Redis Pub/Sub)**: Separate namespace for system notifications
- **Analytics Layer (Redis Queue)**: High-capacity event storage (1hr expiry, 5000 capacity)

**Base Consumer Configuration:**

.. literalinclude:: ../../sandbox_fastapi/base_consumer.py
   :language: python

Environment-driven configuration allows testing with/without completion signals.

System Messaging (No Channel Layers)
------------------------------------

Direct WebSocket communication without channel layers:

.. code-block:: python

   # From sandbox_fastapi/apps/system_chat/consumer.py
   @channel(name="system_chat", description="Direct WebSocket messaging")
   class SystemMessageConsumer(BaseConsumer):
       # No channel_layer_alias - uses direct WebSocket

       @ws_handler(summary="Echo system message")
       async def handle_system_message(self, message: SystemMessage) -> SystemEchoMessage:
           return SystemEchoMessage(
               payload=f"SYSTEM ECHO: {message.payload.message}"
           )

Room Chat Management
--------------------

The room chat consumer demonstrates path parameter handling:

.. code-block:: python

   # From sandbox_fastapi/apps/room_chat/consumer.py
   @channel(name="room_chat", description="Dynamic room-based chat")
   class RoomChatConsumer(BaseConsumer):
       async def post_authentication(self):
           # Extract room from WebSocket path
           room_name = self.scope["path_info"].split("/")[-1]
           await self.join_group(f"room_{room_name}")

       @ws_handler(summary="Send message to room")
       async def handle_room_message(self, message: RoomMessage) -> None:
           room_name = self.scope["path_info"].split("/")[-1]
           await self.broadcast_message(
               RoomNotificationMessage(
                   payload=f"[{room_name}] {message.payload.message}"
               ),
               groups=[f"room_{room_name}"]
           )

Real ARQ Background Job Processing
-----------------------------------

**Complete Job Lifecycle (sandbox_fastapi/tasks.py):**

.. code-block:: python

   # Real ARQ tasks with result streaming back to WebSocket
   async def translate(ctx: dict, job_id: str, content: str, channel_name: str) -> dict:
       """Real translation task with async processing."""
       await asyncio.sleep(2)  # Simulate API call

       translations = {"hello": "hola", "world": "mundo"}
       translated = translations.get(content.lower(), f"[TRANSLATED: {content}]")
       result = f"🌍 Translated: '{content}' → '{translated}'"

       # Send result back to WebSocket client via channel layer
       await _send_result_to_client(channel_name, result)
       return {"status": "completed", "result": result, "job_id": job_id}

   async def analyze(ctx: dict, job_id: str, content: str, channel_name: str) -> dict:
       """Text analysis task."""
       await asyncio.sleep(3)

       word_count = len(content.split())
       char_count = len(content)
       result = f"📊 Analysis: {char_count} chars, {word_count} words"

       await _send_result_to_client(channel_name, result)
       return {"status": "completed", "result": result}

   async def _send_result_to_client(channel_name: str, message: str) -> None:
       """Stream result back to WebSocket consumer."""
       from sandbox_fastapi.apps.background_jobs.consumer import BackgroundJobConsumer
       await BackgroundJobConsumer.send_event(JobResult(payload=message), channel_name)

**ARQ Job Queuing:**

.. code-block:: python

   async def queue_job(job_type: str, content: str, channel_name: str) -> str:
       """Queue job with ARQ and return job ID."""
       redis = await create_pool(REDIS_SETTINGS)

       try:
           job_id = f"{job_type}_{int(time.time())}"
           job = await redis.enqueue_job(job_type, job_id, content, channel_name)
           return job.job_id if job else job_id
       finally:
           await redis.aclose()

**Consumer Integration:**

The BackgroundJobConsumer queues jobs immediately and receives results via events:

.. code-block:: python

   @ws_handler(output_type=JobStatusMessage)
   async def handle_job(self, message: JobMessage) -> None:
       # 1. Queue ARQ job immediately
       job_id = await queue_job(message.payload.type, message.payload.content, self.channel_name)

       # 2. Send confirmation to client
       await self.send_message(JobStatusMessage(payload={
           "status": "queued", "job_id": job_id
       }))

   @event_handler
   async def handle_job_result(self, event: JobResult) -> JobStatusMessage:
       # 3. Receive results from ARQ worker
       return JobStatusMessage(payload={"status": "result", "message": event.payload})

Multi-Layer Consumer Showcase
-----------------------------

The showcase app demonstrates different channel layer types working together:

.. literalinclude:: ../../sandbox_fastapi/apps/showcase/consumer.py
   :language: python

**Key Features:**

1. **Channel-specific configuration** via ``channel_layer_alias``
2. **Group-based broadcasting** for room-like functionality
3. **Event handlers** for server-side message processing
4. **Connection lifecycle** management with join/leave notifications

**WebSocket Mounting:**

WebSocket consumers are mounted as ASGI applications:

.. code-block:: python

   from fastapi import FastAPI
   from sandbox_fastapi.apps.showcase.consumer import (
       ChatConsumer, AnalyticsConsumer, NotificationConsumer
   )

   app = FastAPI()
   ws_router = FastAPI()

   # Mount WebSocket consumers
   ws_router.add_websocket_route("/chat", ChatConsumer.as_asgi())
   ws_router.add_websocket_route("/analytics", AnalyticsConsumer.as_asgi())
   ws_router.add_websocket_route("/notifications", NotificationConsumer.as_asgi())
   ws_router.add_websocket_route("/room/{room_name}", RoomChatConsumer.as_asgi())

   # Mount WebSocket sub-app
   app.mount("/ws", ws_router)

**Testing External Broadcasting:**

The external sender script demonstrates broadcasting events from outside consumers to connected WebSocket clients:

.. code-block:: bash

   # Start the application and visit http://localhost:8080/
   python sandbox_fastapi/start_dev.py

   # In another terminal, run the external sender script
   python sandbox_fastapi/external_sender.py

AsyncAPI Documentation
----------------------

Automatic API documentation generation from decorated consumers:

.. code-block:: python

   from chanx.ext.fast_channels import (
       asyncapi_docs, asyncapi_spec_json, asyncapi_spec_yaml
   )
   from chanx.ext.fast_channels.type_defs import AsyncAPIConfig

   # Configure AsyncAPI
   asyncapi_conf = AsyncAPIConfig(
       description="Websocket API documentation generated by Chanx",
       version="1.0.0",
   )

   @app.get("/asyncapi")
   async def asyncapi_documentation(request: Request) -> HTMLResponse:
       return await asyncapi_docs(request=request, app=app, config=asyncapi_conf)

   @app.get("/asyncapi.json")
   async def asyncapi_json_spec(request: Request) -> JSONResponse:
       return await asyncapi_spec_json(request=request, app=app, config=asyncapi_conf)

The FastAPI integration provides:

- **Interactive documentation** with WebSocket testing capabilities
- **JSON/YAML exports** for API contract sharing
- **Automatic discovery** of all decorated consumers

.. image:: ../_static/asyncapi-fastapi-info.png
   :alt: AsyncAPI Documentation UI showing FastAPI WebSocket endpoints
   :align: center

HTML Client Interface
---------------------

The sandbox includes a complete HTML/JavaScript client for testing:

.. code-block:: html

   <!-- From main.py HTML template -->
   <div class="chat-container">
       <!-- System Messages (No Channel Layer) -->
       <div class="chat-box system-chat">
           <h3>System Messages (No Layer)</h3>
           <form onsubmit="sendSystemMessage(event)">
               <input type="text" placeholder="Type system message..."/>
               <button>Send</button>
           </form>
           <ul id='systemMessages'></ul>
       </div>

       <!-- Room Chat with Dynamic Rooms -->
       <div class="chat-box room-chat">
           <h3>Room Chat</h3>
           <input type="text" id="roomName" placeholder="Enter room name..."/>
           <button onclick="connectToRoom()">Connect</button>
           <ul id='roomMessages'></ul>
       </div>

       <!-- Background Job Processing -->
       <div class="chat-box job-chat">
           <h3>Background Job Processing</h3>
           <select id="jobType">
               <option value="translate">Translation</option>
               <option value="analyze">Text Analysis</option>
           </select>
           <ul id='jobMessages'></ul>
       </div>
   </div>

Production Development Workflow
----------------------------------

**Coordinated FastAPI + ARQ Startup (sandbox_fastapi/start_dev.py):**

.. literalinclude:: ../../sandbox_fastapi/start_dev.py
   :language: python

**Key Features:**

- **Process Management**: Automatic ARQ worker startup before FastAPI
- **Signal Handling**: Graceful shutdown of both processes with Ctrl+C
- **Development Optimized**: FastAPI live reload + ARQ worker coordination
- **Error Recovery**: Proper cleanup on exceptions or forced termination

**Production Benefits:**

- **Realistic Development**: Same ARQ integration as production
- **Job Testing**: Real background job processing during development
- **Resource Cleanup**: Prevents orphaned worker processes
- **Development UX**: Single command starts entire system

Testing
-------

The FastAPI sandbox uses pytest with comprehensive WebSocket testing:

.. code-block:: bash

   # Run all tests
   pytest sandbox_fastapi/tests/

   # Run specific test files
   pytest sandbox_fastapi/tests/test_background_jobs.py
   pytest sandbox_fastapi/tests/test_room_chat.py

   # Run with coverage
   pytest sandbox_fastapi/tests/ --cov=sandbox_fastapi

**WebSocket Testing with Context Managers:**

.. code-block:: python

   # From sandbox_fastapi/tests/test_background_jobs.py
   import pytest
   from chanx.testing import WebsocketCommunicator
   from sandbox_fastapi.apps.background_jobs.consumer import BackgroundJobConsumer

   @pytest.mark.asyncio
   async def test_job_success(bg_worker):
       """Test real ARQ job processing."""
       async with WebsocketCommunicator(
           app, "/ws/background_jobs", consumer=BackgroundJobConsumer
       ) as comm:
           # Skip connection message
           await comm.receive_all_messages(stop_action="job_status")

           # Send job message
           job_message = JobMessage(payload=JobPayload(type="translate", content="hello"))
           await comm.send_message(job_message)

           # Receive queuing and queued messages
           replies = await comm.receive_all_messages()
           assert len(replies) == 2
           assert replies[0].payload["status"] == "queuing"
           assert replies[1].payload["status"] == "queued"

           # Process with real ARQ worker
           await bg_worker.async_run()

           # Receive job result
           results = await comm.receive_all_messages(stop_action=EVENT_ACTION_COMPLETE)
           translated_result = cast(JobStatusMessage, results[0])
           assert "Translated: 'hello' → 'hola'" in translated_result.payload["message"]

**Room Testing with Path Parameters:**

.. code-block:: python

   @pytest.mark.asyncio
   async def test_room_connection():
       """Test dynamic room joining."""
       async with WebsocketCommunicator(
           app, "/ws/room/test-room", consumer=RoomChatConsumer
       ) as comm:
           # Send room message
           await comm.send_message(RoomChatMessage(payload=RoomMessagePayload(message="Hello room")))

           messages = await comm.receive_all_messages()
           assert "Hello room" in messages[0].payload.message
           assert messages[0].payload.room_name == "test-room"

**Testing Features:**

- **pytest-asyncio Integration** for async WebSocket testing
- **WebsocketCommunicator Context Managers** for automatic cleanup
- **Real ARQ Worker Testing** with `bg_worker` fixture
- **Message Type Validation** using Pydantic message objects
- **Completion Signal Testing** with different stop actions
- **Path Parameter Testing** for dynamic routing
- **Multi-Consumer Testing** across different channel layer types

Configuration Patterns
-----------------------

**1. Environment-based Configuration**

.. code-block:: python

   import os

   class BaseConsumer(AsyncJsonWebsocketConsumer):
       send_completion = bool(os.environ.get("SEND_COMPLETION", False))
       log_websocket_message = bool(os.environ.get("LOG_WEBSOCKET", True))

**2. Per-Consumer Overrides**

.. code-block:: python

   @channel(name="analytics")
   class AnalyticsConsumer(BaseConsumer):
       channel_layer_alias = "analytics"  # Use analytics-specific layer
       log_ignored_actions = ["ping", "heartbeat"]  # Don't log frequent events

**3. Dynamic Configuration**

.. code-block:: python

   class RoomChatConsumer(BaseConsumer):
       async def get_groups(self) -> list[str]:
           room_name = self.scope["path_info"].split("/")[-1]
           return [f"room_{room_name}"]

Production Deployment
---------------------

Key considerations for production deployment:

**1. Channel Layer Scaling**
- Use Redis Cluster or RabbitMQ for high-availability channel layers
- Configure appropriate connection pools and timeouts

**2. Background Job Processing**
- Deploy ARQ workers as separate processes/containers
- Use Redis Sentinel for worker queue high availability

**3. WebSocket Load Balancing**
- Configure sticky sessions or use Redis for session storage
- Consider using a WebSocket-aware load balancer

**4. Monitoring and Observability**
- Enable structured logging with correlation IDs
- Monitor WebSocket connection counts and message rates
- Set up health checks for both HTTP and WebSocket endpoints

Learning Path
-------------

To understand the FastAPI integration:

1. **Start with base configuration** (``base_consumer.py``)
2. **Examine the showcase consumers** (``apps/showcase/consumer.py``)
3. **Study channel layer setup** (``layers.py``)
4. **Review background job integration** (``apps/background_jobs/``)
5. **Check the main FastAPI app** (``main.py``)
6. **Run the development script** (``start_dev.py``)
7. **Test with the HTML client** (visit http://localhost:8080)

This example demonstrates how Chanx provides a consistent API across different ASGI frameworks while leveraging each framework's specific strengths.
