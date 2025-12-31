# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class PidFileRecord:
    """
    Best-effort pidfile lifecycle manager for orchestrator processes.
    """

    PID_DIR_NAME = "pids"
    CONTROLLER_PIDFILE = "controller.pid"
    WORKER_PID_PREFIX = "worker_"
    WORKER_UNBOUND_PIDFILE = "worker_unbound.pid"

    def __init__(self, state_dir: Path, pidfile_name: str) -> None:
        """
        Initialize the pidfile record.

        Args:
            state_dir (Path): Coordination state directory.
            pidfile_name (str): Pidfile name to write under the pid directory.
        """
        self._pidfile_path = state_dir / self.PID_DIR_NAME / pidfile_name

    @classmethod
    def for_controller(cls, state_dir: Path) -> PidFileRecord:
        """
        Build the controller pidfile record.
        """
        return cls(state_dir, cls.CONTROLLER_PIDFILE)

    @classmethod
    def for_worker(cls, state_dir: Path, sg_id: ServiceGroupId) -> PidFileRecord:
        """
        Build the worker pidfile record for a bound service group.
        """
        return cls(state_dir, f"{cls.WORKER_PID_PREFIX}{int(sg_id)}.pid")

    @classmethod
    def for_worker_unbound(cls, state_dir: Path) -> PidFileRecord:
        """
        Build the pidfile record for an unbound worker.
        """
        return cls(state_dir, cls.WORKER_UNBOUND_PIDFILE)

    @classmethod
    def for_runtime(
        cls,
        state_dir: Path,
        mode: OrchestratorMode,
        sg_id: ServiceGroupId | None,
    ) -> PidFileRecord | None:
        """
        Build the pidfile record for the runtime mode.
        """
        if mode == OrchestratorMode.CONTROLLER:
            return cls.for_controller(state_dir)
        if mode == OrchestratorMode.WORKER:
            if sg_id is None:
                return cls.for_worker_unbound(state_dir)
            return cls.for_worker(state_dir, sg_id)
        if mode == OrchestratorMode.STANDALONE:
            return cls.for_controller(state_dir)
        if mode == OrchestratorMode.COMBINED:
            return cls.for_controller(state_dir)
        return None

    def __enter__(self) -> PidFileRecord:
        """
        Write the pidfile best-effort.
        """
        self._write()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """
        Remove the pidfile best-effort.
        """
        self._cleanup()

    def _write(self) -> None:
        with contextlib.suppress(Exception):
            self._pidfile_path.parent.mkdir(parents=True, exist_ok=True)
            self._pidfile_path.write_text(f"{os.getpid()}\n", encoding="utf-8")

    def _cleanup(self) -> None:
        with contextlib.suppress(Exception):
            if self._pidfile_path.exists():
                self._pidfile_path.unlink()

    @property
    def pidfile_path(self) -> Path:
        """
        Return the pidfile path.
        """
        return self._pidfile_path


__all__ = [
    "PidFileRecord",
]
