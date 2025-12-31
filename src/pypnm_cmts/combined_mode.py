# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
import os
import threading
from typing import Final

from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.types.orchestrator_types import OrchestratorMode

COMBINED_MODE_ENV = "PYPNM_CMTS_COMBINED_MODE"
_RUNNER_THREAD_NAME = "pypnm-cmts-combined-runner"
_STOP_TIMEOUT_SECONDS: Final[float] = 5.0


def combined_mode_enabled() -> bool:
    """
    Return whether the combined mode runner is requested via environment.
    """
    value = os.environ.get(COMBINED_MODE_ENV, "").strip().lower()
    return value not in ("", "0", "false", "no")


class CombinedModeRunner:
    """
    Manage the in-process runner lifecycle for combined mode.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._launcher = CmtsOrchestratorLauncher(
            config_path=None,
            mode=OrchestratorMode.COMBINED,
            sg_id=None,
        )
        self._thread: threading.Thread | None = None
        self._thread_lock = threading.Lock()

    def start(self) -> None:
        """
        Launch the orchestrator runner in a background thread.
        """
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run,
                name=_RUNNER_THREAD_NAME,
                daemon=True,
            )
            self._thread.start()

    def _run(self) -> None:
        self.logger.info("Combined mode runner starting.")
        try:
            self._launcher.run_forever()
        except Exception:
            self.logger.exception("Combined mode runner terminated unexpectedly.")
        finally:
            self.logger.info("Combined mode runner stopped.")
            with self._thread_lock:
                self._thread = None

    def stop(self) -> None:
        """
        Signal the runner to stop and wait for termination.
        """
        with self._thread_lock:
            thread = self._thread
        self._launcher.stop_runtime()
        if thread is None:
            return
        thread.join(timeout=_STOP_TIMEOUT_SECONDS)
        if thread.is_alive():
            self.logger.warning(
                "Combined mode runner did not stop within %.1f seconds.",
                _STOP_TIMEOUT_SECONDS,
            )


__all__ = [
    "CombinedModeRunner",
    "COMBINED_MODE_ENV",
    "combined_mode_enabled",
]
