# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pathlib
import time
from collections import deque

from pydantic import BaseModel, Field
from pypnm.lib.types import TimestampSec


class WorkerGuardObservationModel(BaseModel):
    """Runtime facts used to decide whether a worker should be restarted."""

    worker_name: str = Field(default="", description="Human-readable worker label.")
    now_epoch: TimestampSec = Field(default=TimestampSec(0), ge=0.0, description="Current epoch seconds.")
    rss_bytes: int | None = Field(default=None, ge=0, description="Current process RSS in bytes, if known.")
    consecutive_error_cycles: int = Field(default=0, ge=0, description="Consecutive cycles that ended with refresh errors.")


class WorkerGuardDecisionModel(BaseModel):
    """Guard decision returned by the shared worker governor."""

    restart_required: bool = Field(default=False, description="True when the worker should be restarted.")
    reasons: list[str] = Field(default_factory=list, description="Human-readable reasons for the decision.")


class WorkerGuardController:
    """Common restart governor shared by long-running worker supervisors."""

    def __init__(
        self,
        *,
        min_restart_interval_seconds: int,
        max_restarts_per_window: int,
        restart_window_seconds: int = 3600,
    ) -> None:
        self._min_restart_interval_seconds = max(0, int(min_restart_interval_seconds))
        self._max_restarts_per_window = max(1, int(max_restarts_per_window))
        self._restart_window_seconds = max(1, int(restart_window_seconds))
        self._restart_times: deque[float] = deque()

    def evaluate(
        self,
        observation: WorkerGuardObservationModel,
        *,
        rss_restart_threshold_bytes: int | None = None,
        max_consecutive_error_cycles: int | None = None,
    ) -> WorkerGuardDecisionModel:
        """Return whether the current worker should be restarted."""
        reasons: list[str] = []

        if (
            rss_restart_threshold_bytes is not None
            and int(rss_restart_threshold_bytes) > 0
            and observation.rss_bytes is not None
            and int(observation.rss_bytes) >= int(rss_restart_threshold_bytes)
        ):
            reasons.append(
                f"rss_bytes={int(observation.rss_bytes)} exceeded threshold_bytes={int(rss_restart_threshold_bytes)}"
            )

        if (
            max_consecutive_error_cycles is not None
            and int(max_consecutive_error_cycles) > 0
            and int(observation.consecutive_error_cycles) >= int(max_consecutive_error_cycles)
        ):
            reasons.append(
                "consecutive_error_cycles="
                f"{int(observation.consecutive_error_cycles)} exceeded limit={int(max_consecutive_error_cycles)}"
            )

        if not reasons:
            return WorkerGuardDecisionModel()

        gate_reason = self._gate_reason(float(time.monotonic()))
        if gate_reason is not None:
            reasons.append(gate_reason)
            return WorkerGuardDecisionModel(restart_required=False, reasons=reasons)

        return WorkerGuardDecisionModel(restart_required=True, reasons=reasons)

    def record_restart(self, now_monotonic: float | None = None) -> None:
        """Record a restart event for future rate-limiting decisions."""
        now_value = float(time.monotonic() if now_monotonic is None else now_monotonic)
        self._prune_restart_times(now_value)
        self._restart_times.append(now_value)

    def _gate_reason(self, now_monotonic: float) -> str | None:
        self._prune_restart_times(now_monotonic)
        if self._restart_times:
            since_last_restart = now_monotonic - float(self._restart_times[-1])
            if since_last_restart < float(self._min_restart_interval_seconds):
                return (
                    "restart suppressed by min_restart_interval_seconds="
                    f"{self._min_restart_interval_seconds}"
                )
        if len(self._restart_times) >= int(self._max_restarts_per_window):
            return (
                "restart suppressed by max_restarts_per_window="
                f"{self._max_restarts_per_window} over {self._restart_window_seconds}s"
            )
        return None

    def _prune_restart_times(self, now_monotonic: float) -> None:
        window_start = now_monotonic - float(self._restart_window_seconds)
        while self._restart_times and float(self._restart_times[0]) < window_start:
            self._restart_times.popleft()


def read_process_rss_bytes() -> int | None:
    """Read the current process RSS from `/proc/self/status`."""
    status_path = pathlib.Path("/proc/self/status")
    if not status_path.is_file():
        return None
    for line in status_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("VmRSS:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            return None
        return int(parts[1]) * 1024
    return None


__all__ = [
    "WorkerGuardController",
    "WorkerGuardDecisionModel",
    "WorkerGuardObservationModel",
    "read_process_rss_bytes",
]
