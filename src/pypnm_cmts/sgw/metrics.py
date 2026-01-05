# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations


class SgwMetrics:
    """Minimal SGW metrics interface for refresh and staleness telemetry."""

    def record_refresh_duration(self, mode: str, duration_ms: float) -> None:
        """Record a refresh duration in milliseconds."""

    def increment_refresh_error(self, mode: str) -> None:
        """Increment a refresh error counter."""

    def increment_staleness(self) -> None:
        """Increment a staleness counter."""


class NoOpSgwMetrics(SgwMetrics):
    """No-op metrics implementation."""

    def record_refresh_duration(self, mode: str, duration_ms: float) -> None:
        return

    def increment_refresh_error(self, mode: str) -> None:
        return

    def increment_staleness(self) -> None:
        return


class InMemorySgwMetrics(SgwMetrics):
    """In-memory metrics collector for tests."""

    def __init__(self) -> None:
        self.refresh_durations_ms: dict[str, list[float]] = {}
        self.refresh_error_counts: dict[str, int] = {}
        self.staleness_count: int = 0

    def record_refresh_duration(self, mode: str, duration_ms: float) -> None:
        values = self.refresh_durations_ms.setdefault(mode, [])
        values.append(float(duration_ms))

    def increment_refresh_error(self, mode: str) -> None:
        current = self.refresh_error_counts.get(mode, 0)
        self.refresh_error_counts[mode] = current + 1

    def increment_staleness(self) -> None:
        self.staleness_count += 1


__all__ = [
    "InMemorySgwMetrics",
    "NoOpSgwMetrics",
    "SgwMetrics",
]
