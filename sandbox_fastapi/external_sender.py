"""
Example of sending messages to WebSocket groups from outside a consumer,
using centralized layer configuration from layers.py.
"""

import asyncio

from fast_channels.layers.registry import channel_layers

from sandbox_fastapi.apps.showcase.consumer import (
    AnalyticsConsumer,
    ChatConsumer,
    NotificationConsumer,
    ReliableChatConsumer,
)
from sandbox_fastapi.apps.showcase.messages import SystemNotify, SystemPeriodicNotify
from sandbox_fastapi.layers import setup_layers

if len(channel_layers) == 0:
    setup_layers()


async def send_chat_message() -> None:
    """
    Send a message to the chat room using the chat layer.
    """
    await ChatConsumer.broadcast_event(
        SystemNotify(payload="🔔 System announcement: Welcome to the chat!")
    )

    print("✅ Chat message sent!")


async def send_reliable_message() -> None:
    """
    Send a message using the queue-based layer for guaranteed delivery.
    """
    await ReliableChatConsumer.broadcast_event(
        SystemNotify(payload="🔒 Important: System maintenance scheduled for tonight"),
    )

    print("✅ Reliable message sent!")


async def send_notification() -> None:
    """
    Send a notification using the notifications layer.
    """
    await NotificationConsumer.broadcast_event(
        SystemNotify(payload="🚨 Alert: High CPU usage detected on server")
    )

    print("✅ Notification sent!")


async def send_analytics_event() -> None:
    """
    Send analytics events using the analytics layer.
    """
    # Send multiple analytics events
    events = [
        "user_login:john_doe",
        "page_view:/dashboard",
        "button_click:export_data",
        "session_duration:1234",
        "error:api_timeout",
    ]

    for event in events:
        await AnalyticsConsumer.broadcast_event(
            SystemNotify(payload=event),
        )
        await asyncio.sleep(0.1)  # Small delay between events

    print(f"✅ Sent {len(events)} analytics events!")


async def periodic_announcements() -> None:
    """
    Send periodic announcements to different channels.
    """
    print("⏰ Starting periodic announcements...")
    for i in range(3):
        # Alternate between different layers
        if i % 2 == 0:
            group = "chat_room"
            message = f"⏰ Hourly chat announcement #{i+1}"
        else:
            group = "notifications"
            message = f"🔔 System status update #{i+1}"

        if group == "chat_room":
            await ChatConsumer.broadcast_event(
                SystemNotify(payload=message),
            )
        else:  # notifications
            await NotificationConsumer.broadcast_event(
                SystemPeriodicNotify(payload=message),
            )

            print(f"✅ Sent announcement #{i+1}")

        await asyncio.sleep(1)  # 1 second between announcements

    print("✅ Periodic announcements complete!")


async def main() -> None:
    """
    Run all external messaging examples.
    """
    print("=== External Messaging with Centralized Layers ===\n")

    # Import layers module to trigger setup

    examples = [
        ("Chat Message", send_chat_message),
        ("Reliable Message", send_reliable_message),
        ("Notification", send_notification),
        ("Analytics Events", send_analytics_event),
        ("Periodic Announcements", periodic_announcements),
    ]

    for name, func in examples:
        print(f"🎯 Running: {name}")
        try:
            await func()
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
        print()  # Add spacing between examples
        await asyncio.sleep(0.5)  # Brief pause between examples

    print("=== All Examples Complete! ===")


if __name__ == "__main__":
    asyncio.run(main())
