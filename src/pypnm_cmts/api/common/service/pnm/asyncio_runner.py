# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from contextlib import suppress
from typing import TypeVar

T = TypeVar("T")


class PnmAsyncioRunner:
    """Run async coroutines on isolated event loops with safe teardown."""

    @staticmethod
    def run_on_isolated_event_loop(coro: Awaitable[T]) -> T:
        loop = asyncio.DefaultEventLoopPolicy().new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            with suppress(Exception):
                pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            with suppress(Exception):
                loop.run_until_complete(loop.shutdown_asyncgens())
            with suppress(Exception):
                loop.run_until_complete(loop.shutdown_default_executor())
            asyncio.set_event_loop(None)
            loop.close()


__all__ = [
    "PnmAsyncioRunner",
]

