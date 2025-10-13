Django Tutorial: Prerequisites
==============================

Welcome to the Chanx Django tutorial! This hands-on tutorial will guide you through building a real-world chat application with Django Channels and Chanx, covering:

- Real-time chat functionality
- AI assistants/agent chat system
- Notification system
- Background task processing with WebSocket notifications

By the end of this tutorial, you'll understand how to use Chanx to create structured, type-safe WebSocket applications with automatic documentation.

What You'll Learn
-----------------

- Setting up Chanx with Django Channels
- Creating WebSocket consumers with type-safe message handling
- Using decorators for automatic message routing
- Broadcasting messages to groups
- Handling channel layer events
- Generating AsyncAPI documentation
- Testing WebSocket consumers

Prerequisites
-------------

Before starting this tutorial, you should have:

**Required Knowledge:**

- Basic understanding of Python and async/await
- Familiarity with Django web framework
- Basic understanding of WebSockets (what they are and why they're useful)
- Some knowledge of Django Channels (recommended but not required - you'll learn as you go)

**Required Tools:**

- **Docker** - For running Redis (used by Django Channels for the channel layer)
- **uv** - Python package installer (https://docs.astral.sh/uv/)
- **Git** - For cloning the tutorial repository

Installing Prerequisites
-------------------------

If you don't have these tools installed:

**Install Docker:**

Visit https://docs.docker.com/get-docker/ and follow the instructions for your operating system.

**Install uv:**

.. code-block:: bash

   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

Getting the Tutorial Code
--------------------------

The tutorial uses a Git repository with multiple branches representing different checkpoints. This allows you to:

- Start from any checkpoint
- Compare your code with the reference implementation
- Reset to a checkpoint if you get stuck

**Clone the Repository:**

.. code-block:: bash

   git clone https://github.com/huynguyengl99/chanx-django-tutorial.git
   cd chanx-django-tutorial

**Available Branches:**

- ``main`` - Full implementation (complete tutorial result)
- ``cp0`` - Starting point of tutorial
- ``cp1`` - Install and setup Chanx package
- ``cp2`` - Implement chat WebSocket
- ``cp3`` - Implement assistants WebSocket
- ``cp4`` - Implement system WebSocket (notifications)
- ``cp5`` - Add integration tests for all WebSocket endpoints

**Switching Between Checkpoints:**

At any time during the tutorial, you can reset to a specific checkpoint:

.. code-block:: bash

   # Reset to checkpoint 0 (starting point)
   git checkout cp0
   git reset --hard

   # Reset to checkpoint 1
   git checkout cp1
   git reset --hard

   # View the final result
   git checkout main

Tutorial Structure
------------------

Each section of this tutorial corresponds to a checkpoint (branch) in the repository:

1. **Part 1: Setup Chanx** - Install Chanx, configure routing, and view AsyncAPI docs
2. **Part 2: Chat WebSocket** - Build a real-time chat room with broadcasting
3. **Part 3: Assistants WebSocket** - Create an AI chat system with streaming responses
4. **Part 4: System WebSocket** - Implement a notification system
5. **Part 5: Integration Tests** - Add comprehensive tests for all WebSocket endpoints

Next Steps
----------

Ready to start? Head to Part 1 to begin setting up Chanx:

.. toctree::
   :maxdepth: 1

   cp0-initial-setup
