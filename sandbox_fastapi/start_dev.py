#!/usr/bin/env python3
"""
Development startup script that runs both FastAPI app and ARQ worker.

Usage:
    python sandbox_fastapi/start_dev.py

This will start:
1. ARQ worker in the background
2. FastAPI application with live reload

Both processes will be managed together and stopped with Ctrl+C.
"""

import signal
import subprocess
import sys
import time
from types import FrameType

import uvicorn


def main() -> None:  # noqa
    """Start both worker and FastAPI app."""
    print("🚀 Starting development environment...")

    # Store process references
    worker_process = None

    def cleanup(signum: int | None = None, frame: FrameType | None = None) -> None:
        """Clean up processes on exit."""
        print("\n🛑 Shutting down...")

        if worker_process:
            print("🔄 Stopping ARQ worker...")
            worker_process.terminate()
            try:
                worker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker_process.kill()

        print("✅ Shutdown complete")
        sys.exit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        # Start ARQ worker using CLI
        print("🔄 Starting ARQ worker...")
        worker_process = subprocess.Popen(
            [sys.executable, "-m", "arq", "sandbox_fastapi.tasks.WorkerSettings"]
        )

        # Give worker a moment to start
        time.sleep(2)

        # Start FastAPI app
        print("🌐 Starting FastAPI application...")
        uvicorn.run("sandbox_fastapi.main:app", host="0.0.0.0", port=8080, reload=True)

        print("\n✅ Development environment ready!")
        print("📱 FastAPI app: http://localhost:8080")
        print("🔄 ARQ worker: running in background")
        print("🛑 Press Ctrl+C to stop both services")

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
