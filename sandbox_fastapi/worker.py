#!/usr/bin/env python3
"""
ARQ Worker for processing background jobs.

Usage:
    python sandbox_fastapi/worker.py

Or better, use the arq CLI directly:
    arq sandbox_fastapi.tasks.WorkerSettings

This script starts an ARQ worker that will process jobs from Redis.
Run this alongside your FastAPI application to handle background job processing.
"""

import os
import subprocess
import sys

# Add the project root to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    """Start the ARQ worker using CLI to avoid event loop issues."""
    print("🔧 Starting ARQ worker using CLI...")
    print("🔗 Connecting to Redis...")
    print("🚀 Starting ARQ worker...")
    print("📋 Jobs will be processed as they arrive...")
    print("🛑 Press Ctrl+C to stop the worker")

    # Use ARQ CLI to avoid event loop conflicts
    try:
        subprocess.run(
            [sys.executable, "-m", "arq", "sandbox_fastapi.tasks.WorkerSettings"],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n🛑 Worker stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
