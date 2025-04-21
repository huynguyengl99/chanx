Examples
========
This section contains complete example applications built with Chanx. Each example demonstrates different aspects of the framework and provides a reference for common patterns and best practices.

Basic Examples
--------------
.. toctree::
   :maxdepth: 1

   basic

The basic example demonstrates a simple WebSocket consumer with authentication and message handling. It's a great starting point for understanding the core concepts of Chanx.

Complete Applications
---------------------
.. toctree::
   :maxdepth: 1

   chat
   dashboard

These examples show more complete applications:

- **Chat Application**: A multi-room chat system with user presence tracking and message history
- **Dashboard**: A real-time dashboard with data updates and user-specific views

Use Cases
---------
Chanx is well-suited for a variety of real-time applications:

Chat and Messaging
^^^^^^^^^^^^^^^^^^
- Multi-user chat rooms
- Private messaging
- Typing indicators
- Message delivery status
- Media sharing

Real-time Dashboards
^^^^^^^^^^^^^^^^^^^^
- Live data visualization
- Analytics dashboards
- System monitoring
- Activity feeds
- Stock/cryptocurrency tickers

Collaborative Applications
^^^^^^^^^^^^^^^^^^^^^^^^^^
- Document collaboration
- Shared whiteboards
- Multi-user editing
- Interactive presentations
- Real-time comments

Notification Systems
^^^^^^^^^^^^^^^^^^^^
- User notifications
- System alerts
- Status updates
- Event broadcasting
- Subscription-based updates

Gaming and Interactive Applications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Turn-based games
- Live betting
- Auction systems
- Interactive polls
- Quiz applications

IoT and Device Communication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Sensor data streaming
- Device status monitoring
- Remote control interfaces
- Home automation dashboards
- Fleet management systems

Getting the Examples
--------------------
The example code is available in the following locations:

1. **GitHub Repository**: [https://github.com/username/chanx-examples](https://github.com/username/chanx-examples)
2. **Documentation Source**: Located in the `examples` directory of the documentation source

Running the Examples
--------------------
Each example includes instructions for:

1. Installation
2. Configuration
3. Running the application
4. Testing

To run any example:

.. code-block:: bash

    # Clone the example repository
    git clone https://github.com/username/chanx-examples.git
    cd chanx-examples

    # Setup virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt

    # Run migrations
    python manage.py migrate

    # Create a superuser (for authentication examples)
    python manage.py createsuperuser

    # Run the development server
    python manage.py runserver

Then access the example at http://localhost:8000/
