# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import threading

_DEFAULT_CHUNK_BYTES = 16 * 1024 * 1024
_retained_blocks: list[bytearray] = []
_lock = threading.Lock()


def retained_debug_memory_bytes() -> int:
    """Return total retained debug-allocation bytes."""
    with _lock:
        return sum(len(block) for block in _retained_blocks)


def allocate_retained_debug_memory_mb(megabytes: int) -> int:
    """Allocate and retain memory in-process for dev memory-guard testing."""
    requested_bytes = max(0, int(megabytes)) * 1024 * 1024
    if requested_bytes <= 0:
        return retained_debug_memory_bytes()
    staged_blocks: list[bytearray] = []
    remaining_bytes = requested_bytes
    while remaining_bytes > 0:
        chunk_bytes = min(_DEFAULT_CHUNK_BYTES, remaining_bytes)
        block = bytearray(chunk_bytes)
        block[0] = 1
        block[-1] = 1
        staged_blocks.append(block)
        remaining_bytes -= chunk_bytes
    with _lock:
        _retained_blocks.extend(staged_blocks)
        return sum(len(block) for block in _retained_blocks)


def clear_retained_debug_memory() -> int:
    """Release retained debug-allocation references and return remaining bytes."""
    with _lock:
        _retained_blocks.clear()
        return 0


__all__ = [
    "allocate_retained_debug_memory_mb",
    "clear_retained_debug_memory",
    "retained_debug_memory_bytes",
]
