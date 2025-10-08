"""AsyncIO compatibility helpers.

Provides a backwards-compatible replacement for ``asyncio.timeout`` so the
codebase can run on Python 3.10 (Render's default runtime) while still using
the modern context-manager API introduced in Python 3.11.

Usage::

    from app.utils.asyncio_compat import async_timeout

    async with async_timeout(5):
        await some_async_call()

When running on Python ≥ 3.11 we delegate to :func:`asyncio.timeout`. On older
versions we emulate the behaviour by cancelling the current task after the
requested delay and translating the resulting ``CancelledError`` into
``TimeoutError`` when the cancellation was triggered by the timeout handler.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


try:  # Python 3.11+
    from asyncio import timeout as async_timeout  # type: ignore
except ImportError:  # pragma: no cover - executed on Python < 3.11

    @asynccontextmanager
    async def async_timeout(delay: float) -> AsyncIterator[None]:
        """Backport of :func:`asyncio.timeout` for Python 3.10.

        We schedule a cancellation of the current task after ``delay`` seconds.
        If the cancellation actually fires we raise ``asyncio.TimeoutError`` to
        match the standard API.
        """

        loop = asyncio.get_running_loop()
        task = asyncio.current_task()

        if task is None:
            # Without a current task there is nothing to cancel; behave as a
            # no-op context manager.
            yield
            return

        timed_out = False

        def _cancel_task() -> None:
            nonlocal timed_out
            timed_out = True
            task.cancel()

        handle = loop.call_later(delay, _cancel_task)

        try:
            yield
        except asyncio.CancelledError as exc:
            if timed_out:
                raise asyncio.TimeoutError() from exc
            raise
        finally:
            handle.cancel()


__all__ = ["async_timeout"]

