# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import contextlib
import os
import signal
import threading
import time
from collections.abc import Callable
from pathlib import Path

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import CoordinationTickResultModel
from pypnm_cmts.lib.types import ServiceGroupId, TickIndex
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class CmtsOrchestratorRuntime:
    """
    Long-running orchestrator runtime that executes coordination ticks.
    """

    STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)
    PID_DIR_NAME = "pids"
    CONTROLLER_PIDFILE = "controller.pid"
    WORKER_PID_PREFIX = "worker_"
    WORKER_UNBOUND_PIDFILE = "worker_unbound.pid"

    def __init__(
        self,
        settings: CmtsOrchestratorSettings,
        manager: CoordinationManager,
        service_groups: list[ServiceGroupId],
        mode: OrchestratorMode,
        sg_id: ServiceGroupId | None,
    ) -> None:
        """
        Initialize the orchestrator runtime.

        Args:
            settings (CmtsOrchestratorSettings): Orchestrator settings instance.
            manager (CoordinationManager): Coordination manager dependency.
            service_groups (list[ServiceGroupId]): Service group inventory for ticks.
            mode (OrchestratorMode): Execution mode (standalone, controller, worker).
            sg_id (ServiceGroupId | None): Optional bound service group id for worker mode.
        """
        self._settings = settings
        self._manager = manager
        self._service_groups = service_groups
        self._mode = mode
        self._sg_id = sg_id
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

        if self._stop_requested:
            with contextlib.suppress(Exception):
                self._manager.release_all()
            return []

        pidfile_path = self._pidfile_path()
        if pidfile_path is not None:
            self._write_pidfile(pidfile_path)

        sleep_fn = sleeper if sleeper is not None else time.sleep
        tick_interval = float(self._settings.tick_interval_seconds)
        results: list[CoordinationTickResultModel] = []
        ticks = 0
        previous_handlers: dict[signal.Signals, object] = {}
        register_signals = threading.current_thread() is threading.main_thread()

        def _handle_stop(signum: int, frame: object | None) -> None:
            self.stop()

        if register_signals:
            for sig in self.STOP_SIGNALS:
                previous_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, _handle_stop)

        try:
            while not self._stop_requested:
                if self._mode == OrchestratorMode.CONTROLLER:
                    tick_result = self._manager.tick_leader_only()
                else:
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
        finally:
            if register_signals:
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)
            with contextlib.suppress(Exception):
                self._manager.release_all()
            if pidfile_path is not None:
                self._remove_pidfile(pidfile_path)

        return results

    def _pidfile_path(self) -> Path | None:
        """
        Resolve the pidfile path for this runtime instance.
        """
        state_dir = Path(self._settings.state_dir)
        pid_dir = state_dir / self.PID_DIR_NAME
        if self._mode == OrchestratorMode.CONTROLLER:
            return pid_dir / self.CONTROLLER_PIDFILE
        if self._mode == OrchestratorMode.WORKER:
            if self._sg_id is None:
                return pid_dir / self.WORKER_UNBOUND_PIDFILE
            return pid_dir / f"{self.WORKER_PID_PREFIX}{int(self._sg_id)}.pid"
        if self._mode == OrchestratorMode.STANDALONE:
            return pid_dir / self.CONTROLLER_PIDFILE
        return None

    def _write_pidfile(self, pidfile_path: Path) -> None:
        """
        Best-effort pidfile write for the runtime instance.
        """
        with contextlib.suppress(Exception):
            pidfile_path.parent.mkdir(parents=True, exist_ok=True)
            pidfile_path.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_pidfile(self, pidfile_path: Path) -> None:
        """
        Best-effort pidfile removal for the runtime instance.
        """
        with contextlib.suppress(Exception):
            if pidfile_path.exists():
                pidfile_path.unlink()


__all__ = [
    "CmtsOrchestratorRuntime",
]
