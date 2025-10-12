from typing import Any

import pytest
import pytest_asyncio
from arq import create_pool
from arq.worker import Worker

from fast_channels.layers.registry import channel_layers

from .layers import setup_layers
from .tasks import REDIS_SETTINGS, WorkerSettings


@pytest_asyncio.fixture(scope="function")
async def bg_worker() -> Any:
    """Create a real ARQ worker for testing."""
    redis = await create_pool(REDIS_SETTINGS)

    worker = Worker(
        functions=WorkerSettings.functions,
        redis_pool=redis,
        burst=True,
        poll_delay=0.1,
    )

    yield worker
    await redis.aclose()


@pytest.fixture(autouse=True, scope="session")
def fresh_redis_layers(worker_id: str) -> None:
    """Create fresh Redis layers for each test."""
    # Clear all existing layers
    if worker_id == "master":
        wid = 0
    else:
        wid = int(worker_id.replace("gw", "")) % 16
    channel_layers.clear()

    # Re-setup with fresh instances
    setup_layers(True, wid)
