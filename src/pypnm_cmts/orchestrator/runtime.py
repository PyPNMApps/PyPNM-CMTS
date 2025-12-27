# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import time
from collections.abc import Callable

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import CoordinationTickResultModel
from pypnm_cmts.lib.types import ServiceGroupId, TickIndex
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class CmtsOrchestratorRuntime:
    """
    Long-running orchestrator runtime that executes coordination ticks.
    """

    def __init__(
        self,
        settings: CmtsOrchestratorSettings,
        manager: CoordinationManager,
        service_groups: list[ServiceGroupId],
        mode: OrchestratorMode,
    ) -> None:
        """
        Initialize the orchestrator runtime.

        Args:
            settings (CmtsOrchestratorSettings): Orchestrator settings instance.
            manager (CoordinationManager): Coordination manager dependency.
            service_groups (list[ServiceGroupId]): Service group inventory for ticks.
            mode (OrchestratorMode): Execution mode (standalone, controller, worker).
        """
        self._settings = settings
        self._manager = manager
        self._service_groups = service_groups
        self._mode = mode
        self._stop_requested = False

    def stop(self) -> None:
        """
        Request that the runtime stop after the current tick.
        """
        self._stop_requested = True

    def run_forever(
        self,
        max_ticks: int | None = None,
        sleeper: Callable[[float], None] | None = None,
        on_tick: Callable[[CoordinationTickResultModel], None] | None = None,
        on_tick_indexed: Callable[[int, CoordinationTickResultModel], None] | None = None,
    ) -> list[CoordinationTickResultModel]:
        """
        Execute coordination ticks until stopped or max_ticks is reached.

        Args:
            max_ticks (int | None): Optional maximum number of ticks to execute.
            sleeper (Callable[[float], None] | None): Optional sleep function for tests.
            on_tick (Callable[[CoordinationTickResultModel], None] | None): Optional per-tick callback.
            on_tick_indexed (Callable[[int, CoordinationTickResultModel], None] | None): Optional per-tick callback with tick index.

        Returns:
            list[CoordinationTickResultModel]: Collected tick results when max_ticks is provided.
        """
        if max_ticks is not None and max_ticks < 0:
            raise ValueError("max_ticks must be non-negative.")

        sleep_fn = sleeper if sleeper is not None else time.sleep
        tick_interval = float(self._settings.tick_interval_seconds)
        results: list[CoordinationTickResultModel] = []
        ticks = 0

        while not self._stop_requested:
            tick_result = self._manager.tick(self._service_groups)
            tick_result = tick_result.model_copy(update={"tick_index": TickIndex(ticks + 1)})
            if max_ticks is not None:
                results.append(tick_result)
            if on_tick is not None:
                on_tick(tick_result)
            if on_tick_indexed is not None:
                on_tick_indexed(ticks + 1, tick_result)

            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            if self._stop_requested:
                break
            sleep_fn(tick_interval)

        return results


__all__ = [
    "CmtsOrchestratorRuntime",
]
