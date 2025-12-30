# FILE: src/pypnm_cmts/orchestrator/pidfile_manager.py
```python
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from pypnm_cmts.lib.types import ServiceGroupId


@dataclass(frozen=True)
class PidFileRecord:
    """
    Context manager that writes and removes a PID file for the current process.
    """

    _pidfile_path: Path

    @property
    def pidfile_path(self) -> Path:
        return self._pidfile_path

    def __enter__(self) -> PidFileRecord:
        self._pidfile_path.parent.mkdir(parents=True, exist_ok=True)
        self._pidfile_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> bool:
        with suppress(Exception):
            self._pidfile_path.unlink()
        return False

    @staticmethod
    def for_controller(state_dir: Path) -> PidFileRecord:
        pid_dir = state_dir / "pids"
        return PidFileRecord(pid_dir / "controller.pid")

    @staticmethod
    def for_worker(state_dir: Path, sg_id: ServiceGroupId) -> PidFileRecord:
        pid_dir = state_dir / "pids"
        return PidFileRecord(pid_dir / f"worker_{int(sg_id)}.pid")

    @staticmethod
    def for_unbound_worker(state_dir: Path) -> PidFileRecord:
        pid_dir = state_dir / "pids"
        return PidFileRecord(pid_dir / "worker_unbound.pid")

    @staticmethod
    def for_runtime(
        state_dir: Path,
        mode: str,
        sg_id: ServiceGroupId | None,
    ) -> PidFileRecord | None:
        if mode == "controller":
            return PidFileRecord.for_controller(state_dir)
        if mode == "worker" and sg_id is not None:
            return PidFileRecord.for_worker(state_dir, sg_id)
        if mode == "worker" and sg_id is None:
            return PidFileRecord.for_unbound_worker(state_dir)
        return None


__all__ = [
    "PidFileRecord",
]
```

# FILE: src/pypnm_cmts/orchestrator/runtime.py
```python
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import signal
import threading
from contextlib import nullcontext, suppress

from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.pidfile_manager import PidFileRecord


STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class CmtsOrchestratorRuntime:
    """
    Runtime loop for coordination ticks with stop control.
    """

    def __init__(
        self,
        manager: CoordinationManager,
        mode: str,
        state_dir,
        sg_id: ServiceGroupId | None = None,
    ) -> None:
        self._manager = manager
        self._mode = mode
        self._state_dir = state_dir
        self._sg_id = sg_id
        self._stop_requested = False

    def stop(self) -> None:
        """
        Request the runtime loop to stop.
        """
        self._stop_requested = True

    def run_forever(
        self,
        service_groups: list[ServiceGroupId],
        tick_interval_seconds: float,
        max_ticks: int | None = None,
        on_tick=None,
        on_tick_indexed=None,
        sleeper=None,
    ) -> list:
        """
        Run the coordination loop until stop or max_ticks is reached.
        """
        pid_record = PidFileRecord.for_runtime(
            state_dir=self._state_dir,
            mode=self._mode,
            sg_id=self._sg_id,
        )
        pid_ctx = pid_record if pid_record is not None else nullcontext()

        if self._stop_requested:
            with pid_ctx:
                with suppress(Exception):
                    self._manager.release_all()
            return []

        results: list = []
        previous_handlers: dict[signal.Signals, object] = {}
        signal_supported = threading.current_thread() is threading.main_thread()

        if signal_supported:
            for sig in STOP_SIGNALS:
                previous_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, self._handle_stop_signal)

        try:
            with pid_ctx:
                tick_index = 0
                while True:
                    if self._stop_requested:
                        break

                    tick_index += 1
                    result = self._manager.tick(service_groups)
                    results.append(result)

                    if on_tick is not None:
                        on_tick(result)
                    if on_tick_indexed is not None:
                        on_tick_indexed(tick_index, result)

                    if max_ticks is not None and tick_index >= max_ticks:
                        break

                    if sleeper is not None:
                        sleeper(tick_interval_seconds)

        finally:
            if signal_supported:
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)
            with suppress(Exception):
                self._manager.release_all()

        return results

    def _handle_stop_signal(self, signum: int, frame: object | None) -> None:
        self._stop_requested = True


__all__ = [
    "CmtsOrchestratorRuntime",
]
```

# FILE: tests/test_pidfile_manager.py
```python
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.pidfile_manager import PidFileRecord


def test_pidfile_written_and_removed_controller(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.getpid", lambda: 12345)
    record = PidFileRecord.for_controller(tmp_path)
    with record:
        assert record.pidfile_path.exists()
        assert record.pidfile_path.read_text(encoding="utf-8").strip() == "12345"
    assert not record.pidfile_path.exists()


def test_pidfile_written_worker_with_sg_id(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.getpid", lambda: 22222)
    record = PidFileRecord.for_worker(tmp_path, ServiceGroupId(7))
    with record:
        assert record.pidfile_path.exists()
        assert record.pidfile_path.read_text(encoding="utf-8").strip() == "22222"
    assert not record.pidfile_path.exists()


def test_pidfile_cleanup_best_effort_does_not_raise(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    record = PidFileRecord.for_controller(tmp_path)
    with record:
        assert record.pidfile_path.exists()

    def _raise_unlink(self: Path) -> None:
        raise OSError("unlink failed")

    record.pidfile_path.write_text("999\n", encoding="utf-8")
    monkeypatch.setattr(Path, "unlink", _raise_unlink)
    record.__exit__(None, None, None)
    assert record.pidfile_path.exists()
```
