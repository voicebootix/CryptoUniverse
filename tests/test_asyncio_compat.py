import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.asyncio_compat import _async_timeout_backport, async_timeout


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout_cm", [async_timeout, _async_timeout_backport])
async def test_async_timeout_clears_cancelled_state(timeout_cm) -> None:
    """After a timeout the surrounding task should not stay cancelled."""

    with pytest.raises(asyncio.TimeoutError):
        async with timeout_cm(0.01):
            await asyncio.sleep(0.05)

    try:
        await asyncio.sleep(0)
    except asyncio.CancelledError as exc:  # pragma: no cover - defensive
        pytest.fail(f"Task remained cancelled after timeout: {exc!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout_cm", [async_timeout, _async_timeout_backport])
async def test_async_timeout_propagates_external_cancellation(timeout_cm) -> None:
    """External cancellation should propagate as ``CancelledError``."""

    loop = asyncio.get_running_loop()
    entered = loop.create_future()

    async def _runner() -> None:
        async with timeout_cm(5):
            entered.set_result(True)
            await asyncio.sleep(10)

    task = loop.create_task(_runner())

    await entered
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
