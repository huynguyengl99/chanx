User Guide
==========
This user guide provides detailed information about each component of Chanx and how to use them effectively in your applications.

Core Components
---------------
Chanx consists of several core components that work together to provide a comprehensive WebSocket framework:


1. **WebSocket Consumers**: Base consumer classes with authentication, messages, and group handling
2. **Message System**: Pydantic-based message validation and routing
3. **Authentication**: DRF-style authentication for WebSocket connections
4. **Testing**: Specialized tools for testing WebSocket endpoints
5. **Playground**: Interactive UI for exploring and testing WebSocket endpoints

Getting Started
---------------
If you're new to Chanx, we recommend working through the guides in this order:

1. Start with :doc:`authentication` to understand how WebSocket connections are secured
2. Move on to :doc:`messages` to learn about structured message handling
3. Explore :doc:`consumers` to see how consumers pull everything together
4. See :doc:`testing` for guidance on testing your WebSocket endpoints
5. Try the :doc:`playground` for interactive exploration of your endpoints

Or jump directly to the guide that addresses your current need.

Contents
--------
.. toctree::
   :maxdepth: 2

   authentication
   messages
   consumers
   testing
   playground

Best Practices
--------------
**Authentication**

* Always use authentication for WebSocket endpoints that access user data
* Keep permission logic consistent between REST API and WebSockets
* Use object-level permissions for endpoints that deal with specific resources

**Messages**

* Define clear message contracts with well-documented types
* Keep message types focused with single responsibilities
* Use strict typing to catch errors early
* Validate complex payloads with Pydantic validators

**Consumers**

* Keep consumers focused on specific domains
* Use type hints for better IDE support
* Document expected message formats
* Implement proper error handling

**Testing**

* Test both happy paths and failure scenarios
* Test reconnection and error handling
* Use the provided WebsocketTestCase for consistent testing
* Mock external dependencies when testing consumers

**General**

* Follow the Django principle of "explicit is better than implicit"
* Use structured logging to track WebSocket activity
* Keep consumers small and focused
* Define clear boundaries between components

Next Steps
----------
After reviewing the user guide, check out the :doc:`/examples/index` for complete applications using Chanx.
