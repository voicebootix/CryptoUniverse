import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.asyncio_compat import async_timeout


@pytest.mark.asyncio
async def test_async_timeout_clears_cancelled_state() -> None:
    """After a timeout the surrounding task should not stay cancelled."""

    with pytest.raises(asyncio.TimeoutError):
        async with async_timeout(0.01):
            await asyncio.sleep(0.05)

    try:
        await asyncio.sleep(0)
    except asyncio.CancelledError as exc:  # pragma: no cover - defensive
        pytest.fail(f"Task remained cancelled after timeout: {exc!r}")


@pytest.mark.asyncio
async def test_async_timeout_propagates_external_cancellation() -> None:
    """External cancellation should propagate as ``CancelledError``."""

    loop = asyncio.get_running_loop()
    entered = loop.create_future()

    async def _runner() -> None:
        async with async_timeout(5):
            entered.set_result(True)
            await asyncio.sleep(10)

    task = loop.create_task(_runner())

    await entered
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
