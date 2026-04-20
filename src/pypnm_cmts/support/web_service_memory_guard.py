# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging
import threading

from pypnm.lib.types import TimestampSec

from pypnm_cmts.config.system_config_settings import CmtsSystemConfigSettings
from pypnm_cmts.support.web_service_reload import request_web_service_reload
from pypnm_cmts.support.worker_guard import (
    WorkerGuardController,
    WorkerGuardObservationModel,
    read_process_rss_bytes,
)

WEB_SERVICE_MEMORY_GUARD_THREAD_NAME = "pypnm-cmts-web-memory-guard"
DEFAULT_WEB_SERVICE_MEMORY_GUARD_STOP_TIMEOUT_SECONDS = 2.0


class WebServiceMemoryGuard:
    """Process-level RSS guard that requests web-service reloads on threshold breach."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._controller: WorkerGuardController | None = None

    def start(self) -> bool:
        """Start the background web-service RSS guard when enabled."""
        if not bool(CmtsSystemConfigSettings.web_service_memory_guard_enabled()):
            return False
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return True
            self._stop_event.clear()
            self._controller = WorkerGuardController(
                min_restart_interval_seconds=int(CmtsSystemConfigSettings.web_service_memory_guard_min_restart_interval_seconds()),
                max_restarts_per_window=int(CmtsSystemConfigSettings.web_service_memory_guard_max_restarts_per_hour()),
            )
            self._thread = threading.Thread(
                target=self._run_loop,
                name=WEB_SERVICE_MEMORY_GUARD_THREAD_NAME,
                daemon=True,
            )
            self._thread.start()
        return True

    def stop(self, timeout_seconds: float = DEFAULT_WEB_SERVICE_MEMORY_GUARD_STOP_TIMEOUT_SECONDS) -> None:
        """Stop the background web-service RSS guard if it is running."""
        self._stop_event.set()
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout=float(timeout_seconds))
        with self._lock:
            if self._thread is thread and (thread is None or not thread.is_alive()):
                self._thread = None
                self._controller = None

    def evaluate_once(self, *, now_epoch: TimestampSec | None = None) -> bool:
        """Evaluate current process RSS and request reload when guard policy requires it."""
        controller = self._controller
        if controller is None:
            controller = WorkerGuardController(
                min_restart_interval_seconds=int(CmtsSystemConfigSettings.web_service_memory_guard_min_restart_interval_seconds()),
                max_restarts_per_window=int(CmtsSystemConfigSettings.web_service_memory_guard_max_restarts_per_hour()),
            )
            self._controller = controller
        rss_threshold_mb = int(CmtsSystemConfigSettings.web_service_memory_guard_rss_restart_threshold_mb())
        if rss_threshold_mb <= 0:
            return False
        rss_bytes = read_process_rss_bytes()
        decision = controller.evaluate(
            WorkerGuardObservationModel(
                worker_name=WEB_SERVICE_MEMORY_GUARD_THREAD_NAME,
                now_epoch=TimestampSec(0 if now_epoch is None else now_epoch),
                rss_bytes=rss_bytes,
                consecutive_error_cycles=0,
            ),
            rss_restart_threshold_bytes=rss_threshold_mb * 1024 * 1024,
            max_consecutive_error_cycles=0,
        )
        if not bool(decision.restart_required):
            return False
        reason = "; ".join(reason_text.strip() for reason_text in decision.reasons if reason_text.strip() != "")
        if reason == "":
            reason = f"rss_bytes={rss_bytes} exceeded threshold_mb={rss_threshold_mb}"
        self._logger.warning(
            "[WEBSERVICE_MEMORY_GUARD_RELOAD] reason=%s rss_bytes=%s threshold_mb=%s",
            reason,
            rss_bytes,
            rss_threshold_mb,
        )
        request_web_service_reload(
            reason="memory_guard_rss_threshold",
            actor="cmts.system.webService.memoryGuard",
        )
        controller.record_restart()
        return True

    def _run_loop(self) -> None:
        """Internal-only loop for periodic process RSS evaluation."""
        poll_seconds = max(1, int(CmtsSystemConfigSettings.web_service_memory_guard_poll_seconds()))
        while not self._stop_event.wait(float(poll_seconds)):
            self.evaluate_once()
