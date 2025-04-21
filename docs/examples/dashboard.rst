Real-Time Dashboard Example
===========================
This example demonstrates building a real-time dashboard with Chanx. The dashboard displays live data updates, user-specific views, and interactive charts that update in real-time without page refresh.

Project Overview
----------------
Our dashboard application demonstrates:

1. Authenticated WebSocket connections with object-level permissions
2. Data streaming to specific user groups
3. Real-time chart and visualization updates
4. Background data collection/processing with WebSocket publishing
5. Client-side rendering of streamed data

This example is more complex than the basic echo example and the chat application, showing how Chanx can be used for business applications with real-time data requirements.

Project Structure
-----------------
.. code-block:: bash

    dashboard_project/
    ├── manage.py
    ├── dashboard_project/
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    └── dashboard/
        ├── __init__.py
        ├── admin.py
        ├── consumers.py
        ├── management/
        │   └── commands/
        │       └── generate_data.py
        ├── messages.py
        ├── models.py
        ├── permissions.py
        ├── routing.py
        ├── tasks.py
        ├── templates/
        │   └── dashboard/
        │       ├── index.html
        │       └── metrics.html
        ├── urls.py
        └── views.py

Models
------
First, let's define our data models in `dashboard/models.py`:

.. code-block:: python

    from django.db import models
    from django.contrib.auth.models import User


    class Dashboard(models.Model):
        """Dashboard model representing a collection of metrics."""
        name = models.CharField(max_length=100)
        slug = models.SlugField(unique=True)
        description = models.TextField(blank=True)
        created_at = models.DateTimeField(auto_now_add=True)
        users = models.ManyToManyField(User, related_name="dashboards")

        def __str__(self):
            return self.name


    class Metric(models.Model):
        """Metric model representing a specific data point to track."""
        TYPES = (
            ("counter", "Counter"),
            ("gauge", "Gauge"),
            ("histogram", "Histogram"),
        )

        dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="metrics")
        name = models.CharField(max_length=100)
        description = models.TextField(blank=True)
        metric_type = models.CharField(max_length=20, choices=TYPES)
        unit = models.CharField(max_length=50, blank=True)

        def __str__(self):
            return f"{self.name} ({self.get_metric_type_display()})"


    class MetricValue(models.Model):
        """Individual metric value recorded at a point in time."""
        metric = models.ForeignKey(Metric, on_delete=models.CASCADE, related_name="values")
        value = models.FloatField()
        timestamp = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-timestamp"]

        def __str__(self):
            return f"{self.metric.name}: {self.value} at {self.timestamp}"

Message Types
-------------
Define message types in `dashboard/messages.py`:

.. code-block:: python

    from typing import Dict, List, Literal, Optional, Union, Any
    from datetime import datetime

    from pydantic import Field

    from chanx.messages.base import BaseIncomingMessage, BaseMessage
    from chanx.messages.incoming import PingMessage


    class MetricUpdatePayload(BaseModel):
        """Payload for metric update messages."""
        metric_id: int
        value: float
        timestamp: str
        metric_name: Optional[str] = None
        unit: Optional[str] = None


    class MetricUpdateMessage(BaseMessage):
        """Message for sending metric updates."""
        action: Literal["metric_update"] = "metric_update"
        payload: MetricUpdatePayload


    class MetricHistoryPayload(BaseModel):
        """Payload for metric history messages."""
        metric_id: int
        values: List[Dict[str, Union[float, str]]]
        metric_name: str
        unit: Optional[str] = None


    class MetricHistoryMessage(BaseMessage):
        """Message for sending historical metric data."""
        action: Literal["metric_history"] = "metric_history"
        payload: MetricHistoryPayload


    class SubscribeMessage(BaseMessage):
        """Message for subscribing to specific metrics."""
        action: Literal["subscribe"] = "subscribe"
        payload: List[int]  # List of metric IDs


    class UnsubscribeMessage(BaseMessage):
        """Message for unsubscribing from specific metrics."""
        action: Literal["unsubscribe"] = "unsubscribe"
        payload: List[int]  # List of metric IDs


    class DashboardConfigMessage(BaseMessage):
        """Message for sending dashboard configuration."""
        action: Literal["dashboard_config"] = "dashboard_config"
        payload: Dict[str, Any]


    class DashboardIncomingMessage(BaseIncomingMessage):
        """Container for all dashboard incoming message types."""
        message: PingMessage | SubscribeMessage | UnsubscribeMessage

Permissions
-----------
Create custom permissions in `dashboard/permissions.py`:

.. code-block:: python

    from rest_framework.permissions import BasePermission


    class IsDashboardMember(BasePermission):
        """
        Permission to check if a user has access to a dashboard.
        """
        def has_object_permission(self, request, view, obj):
            # Check if the user is in the dashboard's users list
            return request.user in obj.users.all()

Consumer Implementation
-----------------------
Implement the dashboard consumer in `dashboard/consumers.py`:

.. code-block:: python

    from typing import Iterable, List, Set, Dict, Any, cast

    from asgiref.sync import sync_to_async
    from channels.db import database_sync_to_async
    from django.contrib.auth.models import User
    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.messages.outgoing import PongMessage
    from chanx.utils.asyncio import create_task

    from dashboard.models import Dashboard, Metric, MetricValue
    from dashboard.messages import (
        DashboardIncomingMessage,
        MetricUpdateMessage,
        MetricHistoryMessage,
        DashboardConfigMessage,
    )
    from dashboard.permissions import IsDashboardMember


    class DashboardConsumer(AsyncJsonWebsocketConsumer):
        """WebSocket consumer for real-time dashboard updates."""

        # Authentication configuration
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated, IsDashboardMember]
        queryset = Dashboard.objects.all()

        # Message schema
        INCOMING_MESSAGE_SCHEMA = DashboardIncomingMessage

        # Enable completion messages
        send_completion = True

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.subscribed_metrics: Set[int] = set()

        async def build_groups(self) -> Iterable[str]:
            """Build channel groups based on the dashboard."""
            dashboard = cast(Dashboard, self.obj)
            return [f"dashboard_{dashboard.id}"]

        async def post_authentication(self) -> None:
            """Actions after successful authentication."""
            dashboard = cast(Dashboard, self.obj)

            # Send dashboard configuration
            await self.send_dashboard_config(dashboard)

            # Send initial historical data for all metrics
            for metric in await self.get_dashboard_metrics(dashboard):
                self.subscribed_metrics.add(metric.id)
                await self.send_metric_history(metric)

        @database_sync_to_async
        def get_dashboard_metrics(self, dashboard: Dashboard) -> List[Metric]:
            """Get all metrics for a dashboard."""
            return list(dashboard.metrics.all())

        async def send_dashboard_config(self, dashboard: Dashboard) -> None:
            """Send dashboard configuration to the client."""
            # Get dashboard data
            dashboard_data = await self.get_dashboard_data(dashboard)

            # Send configuration message
            await self.send_message(
                DashboardConfigMessage(payload=dashboard_data)
            )

        @database_sync_to_async
        def get_dashboard_data(self, dashboard: Dashboard) -> Dict[str, Any]:
            """Get dashboard data for configuration message."""
            metrics = []

            for metric in dashboard.metrics.all():
                metrics.append({
                    "id": metric.id,
                    "name": metric.name,
                    "description": metric.description,
                    "type": metric.metric_type,
                    "unit": metric.unit,
                })

            return {
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
                "metrics": metrics,
            }

        async def send_metric_history(self, metric: Metric) -> None:
            """Send historical data for a metric."""
            # Get historical values
            history = await self.get_metric_history(metric)

            # Send history message
            await self.send_message(
                MetricHistoryMessage(
                    payload={
                        "metric_id": metric.id,
                        "values": history,
                        "metric_name": metric.name,
                        "unit": metric.unit,
                    }
                )
            )

        @database_sync_to_async
        def get_metric_history(self, metric: Metric, limit: int = 100) -> List[Dict[str, Any]]:
            """Get historical values for a metric."""
            values = []

            for value in metric.values.all()[:limit]:
                values.append({
                    "value": value.value,
                    "timestamp": value.timestamp.isoformat(),
                })

            return values

        async def receive_message(self, message, **kwargs):
            """Handle incoming messages."""
            if message.action == "ping":
                # Respond to ping
                await self.send_message(PongMessage())

            elif message.action == "subscribe":
                # Subscribe to metrics
                await self.handle_subscribe(message.payload)

            elif message.action == "unsubscribe":
                # Unsubscribe from metrics
                await self.handle_unsubscribe(message.payload)

        async def handle_subscribe(self, metric_ids: List[int]) -> None:
            """Handle subscription to metrics."""
            dashboard = cast(Dashboard, self.obj)

            # Add metrics to subscription set
            self.subscribed_metrics.update(metric_ids)

            # Send historical data for newly subscribed metrics
            for metric_id in metric_ids:
                metric = await self.get_metric_by_id(dashboard, metric_id)
                if metric:
                    await self.send_metric_history(metric)

        async def handle_unsubscribe(self, metric_ids: List[int]) -> None:
            """Handle unsubscription from metrics."""
            # Remove metrics from subscription set
            self.subscribed_metrics.difference_update(metric_ids)

        @database_sync_to_async
        def get_metric_by_id(self, dashboard: Dashboard, metric_id: int) -> Optional[Metric]:
            """Get a metric by ID, ensuring it belongs to the dashboard."""
            try:
                return dashboard.metrics.get(id=metric_id)
            except Metric.DoesNotExist:
                return None

        # Handle metric updates from background tasks
        async def metric_update(self, event: Dict[str, Any]) -> None:
            """Handle metric update events from channel layer."""
            metric_id = event["metric_id"]

            # Only forward updates for subscribed metrics
            if metric_id in self.subscribed_metrics:
                # Send update to the client
                await self.send_message(
                    MetricUpdateMessage(
                        payload={
                            "metric_id": metric_id,
                            "value": event["value"],
                            "timestamp": event["timestamp"],
                            "metric_name": event.get("metric_name"),
                            "unit": event.get("unit"),
                        }
                    )
                )

Background Data Generation
--------------------------
Create a task that simulates data generation in `dashboard/tasks.py`:

.. code-block:: python

    import asyncio
    import random
    from datetime import datetime
    from typing import Optional

    from asgiref.sync import sync_to_async
    from channels.layers import get_channel_layer
    from django.utils import timezone

    from dashboard.models import Dashboard, Metric, MetricValue


    async def generate_metric_value(metric: Metric) -> float:
        """Generate a random metric value based on the metric type."""
        if metric.metric_type == "counter":
            # Counters always increase
            latest_value = await get_latest_value(metric)
            return latest_value + random.uniform(1, 10)

        elif metric.metric_type == "gauge":
            # Gauges fluctuate around a value
            return random.uniform(10, 100)

        elif metric.metric_type == "histogram":
            # Histograms distribute across a range
            return random.normalvariate(50, 15)

        # Default
        return random.uniform(0, 100)


    @sync_to_async
    def get_latest_value(metric: Metric) -> float:
        """Get the latest value for a metric, or 0 if none exists."""
        try:
            latest = metric.values.first()
            return latest.value if latest else 0
        except Exception:
            return 0


    @sync_to_async
    def save_metric_value(metric: Metric, value: float) -> MetricValue:
        """Save a new metric value to the database."""
        return MetricValue.objects.create(
            metric=metric,
            value=value,
        )


    async def publish_metric_update(
        metric: Metric, value: float, dashboard_id: int
    ) -> None:
        """Publish a metric update to the channel layer."""
        channel_layer = get_channel_layer()

        # Format the timestamp
        timestamp = timezone.now().isoformat()

        # Send to the dashboard group
        await channel_layer.group_send(
            f"dashboard_{dashboard_id}",
            {
                "type": "metric_update",
                "metric_id": metric.id,
                "value": value,
                "timestamp": timestamp,
                "metric_name": metric.name,
                "unit": metric.unit,
            },
        )


    async def update_metrics_task() -> None:
        """Background task to update metrics and publish changes."""
        # Import here to avoid circular imports
        from dashboard.models import Dashboard, Metric

        while True:
            try:
                # Get all dashboards and metrics
                dashboards = await sync_to_async(list)(Dashboard.objects.all())

                for dashboard in dashboards:
                    metrics = await sync_to_async(list)(dashboard.metrics.all())

                    for metric in metrics:
                        # Generate a new value
                        value = await generate_metric_value(metric)

                        # Save to database
                        await save_metric_value(metric, value)

                        # Publish update
                        await publish_metric_update(metric, value, dashboard.id)

                # Wait before next update
                await asyncio.sleep(5)  # Update every 5 seconds

            except Exception as e:
                print(f"Error in update task: {e}")
                await asyncio.sleep(10)  # Wait longer on error

WebSocket Routing
-----------------
Set up routing in `dashboard/routing.py`:

.. code-block:: python

    from django.urls import re_path

    from dashboard.consumers import DashboardConsumer

    websocket_urlpatterns = [
        re_path(r"ws/dashboard/(?P<pk>\d+)/$", DashboardConsumer.as_asgi()),
    ]

Frontend Implementation
-----------------------
Create a dashboard template in `dashboard/templates/dashboard/index.html`:

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ dashboard.name }} - Real-Time Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }
            .dashboard-header {
                margin-bottom: 20px;
            }
            .metrics-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
                gap: 20px;
            }
            .metric-card {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .metric-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }
            .metric-title {
                font-weight: bold;
                font-size: 18px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-unit {
                font-size: 14px;
                color: #666;
            }
            .chart-container {
                height: 200px;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="dashboard-header">
            <h1>{{ dashboard.name }}</h1>
            <p>{{ dashboard.description }}</p>
        </div>

        <div class="metrics-container" id="metrics-container">
            <!-- Metrics will be added here dynamically -->
            <div class="loading">Loading dashboard data...</div>
        </div>

        <script>
            // Dashboard state
            const dashboardId = {{ dashboard.id }};
            const metricData = {};
            const metricCharts = {};

            // Connection status
            let isConnected = false;
            let socket;

            // Connect to the WebSocket
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
                const wsUrl = `${protocol}${window.location.host}/ws/dashboard/${dashboardId}/`;

                console.log(`Connecting to ${wsUrl}`);
                socket = new WebSocket(wsUrl);

                // Connection opened
                socket.addEventListener('open', (event) => {
                    console.log('Connected to dashboard WebSocket');
                    isConnected = true;
                });

                // Listen for messages
                socket.addEventListener('message', (event) => {
                    const data = JSON.parse(event.data);
                    console.log('Message received:', data);

                    // Handle different message types
                    switch (data.action) {
                        case 'dashboard_config':
                            handleDashboardConfig(data.payload);
                            break;
                        case 'metric_history':
                            handleMetricHistory(data.payload);
                            break;
                        case 'metric_update':
                            handleMetricUpdate(data.payload);
                            break;
                        case 'authentication':
                            handleAuthentication(data.payload);
                            break;
                        case 'error':
                            handleError(data.payload);
                            break;
                    }
                });

                // Connection closed
                socket.addEventListener('close', (event) => {
                    console.log('Disconnected from WebSocket');
                    isConnected = false;

                    // Try to reconnect after 3 seconds
                    setTimeout(() => {
                        if (!isConnected) {
                            connect();
                        }
                    }, 3000);
                });

                // Connection error
                socket.addEventListener('error', (event) => {
                    console.error('WebSocket error:', event);
                });
            }

            // Handle dashboard configuration
            function handleDashboardConfig(config) {
                console.log('Received dashboard config:', config);

                // Clear loading indicator
                document.getElementById('metrics-container').innerHTML = '';

                // Create metric cards
                config.metrics.forEach(metric => {
                    createMetricCard(metric);
                });
            }

            // Create a metric card
            function createMetricCard(metric) {
                const container = document.getElementById('metrics-container');

                // Create card element
                const card = document.createElement('div');
                card.className = 'metric-card';
                card.id = `metric-card-${metric.id}`;

                // Create header
                const header = document.createElement('div');
                header.className = 'metric-header';

                const title = document.createElement('div');
                title.className = 'metric-title';
                title.textContent = metric.name;

                const type = document.createElement('div');
                type.className = 'metric-type';
                type.textContent = metric.type;

                header.appendChild(title);
                header.appendChild(type);

                // Create value display
                const valueDisplay = document.createElement('div');
                valueDisplay.className = 'metric-value';
                valueDisplay.id = `metric-value-${metric.id}`;
                valueDisplay.textContent = '–';

                if (metric.unit) {
                    const unitSpan = document.createElement('span');
                    unitSpan.className = 'metric-unit';
                    unitSpan.textContent = ` ${metric.unit}`;
                    valueDisplay.appendChild(unitSpan);
                }

                // Create chart container
                const chartContainer = document.createElement('div');
                chartContainer.className = 'chart-container';

                const canvas = document.createElement('canvas');
                canvas.id = `chart-${metric.id}`;
                chartContainer.appendChild(canvas);

                // Assemble card
                card.appendChild(header);
                card.appendChild(valueDisplay);
                card.appendChild(chartContainer);

                // Add to container
                container.appendChild(card);

                // Initialize empty data
                metricData[metric.id] = {
                    values: [],
                    labels: [],
                    config: metric
                };

                // Create chart
                createChart(metric.id, metric.type);
            }

            // Create a chart for a metric
            function createChart(metricId, metricType) {
                const canvas = document.getElementById(`chart-${metricId}`);

                let chartType = 'line';
                if (metricType === 'histogram') {
                    chartType = 'bar';
                }

                const chart = new Chart(canvas, {
                    type: chartType,
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Value',
                            data: [],
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            borderWidth: 2,
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: metricType !== 'counter'
                            },
                            x: {
                                display: true
                            }
                        },
                        animation: {
                            duration: 300
                        }
                    }
                });

                metricCharts[metricId] = chart;
            }

            // Handle metric history
            function handleMetricHistory(data) {
                console.log('Received metric history:', data);

                // Implementation continued in the full example code
                // For brevity in documentation, we're showing just the key concepts
            }

            // Connect when the page loads
            document.addEventListener('DOMContentLoaded', connect);
        </script>
    </body>
    </html>

Using the Playground Instead
----------------------------
Instead of building a custom frontend, you can use the built-in Chanx WebSocket playground to interact with your dashboard API. This approach lets you avoid writing HTML, JS, and CSS code while still being able to test and demonstrate your real-time dashboard functionality.

To use the playground:

1. Ensure the playground URLs are included in your project:

   .. code-block:: python

       # urls.py
       from django.urls import path, include

       urlpatterns = [
           # ...
           path('chanx/', include('chanx.playground.urls')),
           # ...
       ]

2. Access the playground at http://localhost:8000/chanx/playground/websocket/

3. Connect to your dashboard WebSocket endpoint:

   - Select the dashboard endpoint (e.g., `/ws/dashboard/1/`)
   - Fill in any required parameters (e.g., the dashboard ID)
   - Add your authentication credentials
   - Click "Connect"

4. Once connected, you can:

   - See the initial dashboard configuration
   - Observe real-time metric updates
   - Send subscription/unsubscription messages
   - Test different message formats

Example Playground Messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Here are some example messages you can send using the playground:

**Subscribe to specific metrics:**

.. code-block:: json

    {
        "action": "subscribe",
        "payload": [1, 2, 3]
    }

**Unsubscribe from metrics:**

.. code-block:: json

    {
        "action": "unsubscribe",
        "payload": [3]
    }

**Send a ping message:**

.. code-block:: json

    {
        "action": "ping"
    }

Using the playground eliminates the need to write frontend code while still allowing you to test and demonstrate the real-time capabilities of your dashboard.

Management Command for Data Generation
--------------------------------------
Create a management command to start the data generation task in `dashboard/management/commands/generate_data.py`:

.. code-block:: python

    import asyncio
    import sys
    from django.core.management.base import BaseCommand

    class Command(BaseCommand):
        help = 'Start generating metrics data for dashboards'

        def handle(self, *args, **options):
            from dashboard.tasks import update_metrics_task

            self.stdout.write(self.style.SUCCESS('Starting metrics generation...'))

            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(update_metrics_task())
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Stopping metrics generation...'))
                sys.exit(0)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error: {e}'))
                sys.exit(1)

Starting the Data Generation
----------------------------
To start generating data:

.. code-block:: bash

    python manage.py generate_data

This command will start the background task that generates random metric values and publishes them to connected WebSocket clients.

Testing the Dashboard Consumer
------------------------------
Here's how to test the dashboard consumer:

.. code-block:: python

    from django.contrib.auth.models import User

    from chanx.testing import WebsocketTestCase
    from dashboard.models import Dashboard, Metric
    from dashboard.messages import SubscribeMessage


    class DashboardConsumerTests(WebsocketTestCase):
        """Tests for the DashboardConsumer."""

        def setUp(self):
            super().setUp()
            # Create test user
            self.user = User.objects.create_user(
                username="testuser",
                password="testpassword"
            )

            # Create test dashboard
            self.dashboard = Dashboard.objects.create(
                name="Test Dashboard",
                slug="test-dashboard"
            )
            self.dashboard.users.add(self.user)

            # Create test metrics
            self.metric1 = Metric.objects.create(
                dashboard=self.dashboard,
                name="Test Metric 1",
                metric_type="counter"
            )

            self.metric2 = Metric.objects.create(
                dashboard=self.dashboard,
                name="Test Metric 2",
                metric_type="gauge"
            )

            # Set WebSocket path
            self.ws_path = f"/ws/dashboard/{self.dashboard.id}/"

            # Log in with the test client
            self.client.login(username="testuser", password="testpassword")

        def get_ws_headers(self):
            """Provide session cookie for WebSocket authentication."""
            cookies = self.client.cookies
            return [
                (b"cookie", f"sessionid={cookies['sessionid'].value}".encode()),
            ]

        async def test_connect_and_receive_config(self):
            """Test connecting to dashboard and receiving configuration."""
            # Create a WebSocket communicator
            communicator = self.create_communicator()

            # Connect to the WebSocket
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Verify authentication succeeded
            await communicator.assert_authenticated_status_ok()

            # Should receive dashboard configuration
            received_messages = await communicator.receive_all_json()

            # Find the dashboard_config message
            config_message = next(
                (msg for msg in received_messages if msg.get("action") == "dashboard_config"),
                None
            )

            # Verify configuration
            self.assertIsNotNone(config_message)
            self.assertEqual(config_message["payload"]["id"], self.dashboard.id)
            self.assertEqual(len(config_message["payload"]["metrics"]), 2)

            # Disconnect
            await communicator.disconnect()

        async def test_subscribe_to_metrics(self):
            """Test subscribing to specific metrics."""
            communicator = self.create_communicator()
            await communicator.connect()

            # Wait for initial messages
            await communicator.receive_all_json()

            # Subscribe to a specific metric
            await communicator.send_message(
                SubscribeMessage(payload=[self.metric1.id])
            )

            # Should receive metric history
            response = await communicator.receive_all_json()

            # Find the metric_history message
            history_message = next(
                (msg for msg in response if msg.get("action") == "metric_history"),
                None
            )

            self.assertIsNotNone(history_message)
            self.assertEqual(history_message["payload"]["metric_id"], self.metric1.id)

            await communicator.disconnect()

Key Concepts Demonstrated
-------------------------
This example demonstrates several advanced Chanx features:

1. **Object-Level Permissions**: Using IsDashboardMember to restrict access to specific dashboards
2. **Selective Subscriptions**: Allowing clients to subscribe to specific metrics
3. **Background Data Generation**: Using async tasks to generate and publish data
4. **Channel Layer Broadcasting**: Publishing updates to groups of connected clients
5. **Playground Integration**: Testing and demonstrating WebSocket APIs without custom frontend code

Next Steps
----------
To extend this example, you could:

1. **Add Real Data Sources**: Replace random data with real metrics from databases, APIs, or system monitoring
2. **Implement Alerting**: Add threshold-based alerts when metrics exceed certain values
3. **Add User Preferences**: Store and respect user display preferences for the dashboard
4. **Support Dashboard Editing**: Allow users to customize which metrics appear on their dashboard
5. **Add Data Export**: Implement functionality to export metric data for analysis

For more examples, see the :doc:`chat` application which demonstrates different Chanx features.
