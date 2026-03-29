# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import threading
from collections.abc import Callable

from pydantic import BaseModel, Field
from pypnm.lib.types import TimestampSec

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SGW_LAST_ERROR_MAX_LENGTH
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.store import SgwCacheStore
from pypnm_cmts.support.worker_guard import (
    WorkerGuardController,
    WorkerGuardObservationModel,
    read_process_rss_bytes,
)

DEFAULT_SGW_STARTUP_ERROR = "sgw startup failed"
DEFAULT_SGW_REFRESH_STOP_TIMEOUT_SECONDS = 5.0
SGW_REFRESH_THREAD_NAME = "pypnm-cmts-sgw-refresh"


class SgwStartupStatusModel(BaseModel):
    """Runtime startup status for SGW discovery and priming."""

    startup_completed: bool = Field(default=False, description="Whether SGW startup has completed.")
    discovery_ok: bool = Field(default=False, description="Whether SG discovery completed successfully.")
    discovered_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Discovered service group identifiers.")
    last_refresh_epoch: TimestampSec | None = Field(default=None, ge=0.0, description="Epoch timestamp for the last SGW refresh.")
    error_message: str = Field(default="", max_length=SGW_LAST_ERROR_MAX_LENGTH, description="Bounded startup error message.")
    prime_failed: bool = Field(default=False, description="Whether SGW priming failed after discovery.")
    guard_restart_count: int = Field(default=0, ge=0, description="Number of guard-triggered SGW restarts in this process.")
    last_guard_reason: str = Field(default="", max_length=SGW_LAST_ERROR_MAX_LENGTH, description="Most recent guard restart reason.")
    last_guard_restart_epoch: TimestampSec | None = Field(default=None, ge=0.0, description="Epoch timestamp of the most recent guard restart.")


_sgw_status = SgwStartupStatusModel()
_sgw_store: SgwCacheStore | None = None
_sgw_manager: SgwManager | None = None
_sgw_refresh_thread: threading.Thread | None = None
_sgw_refresh_running = False
_sgw_refresh_lock = threading.Lock()


def reset_sgw_runtime_state() -> None:
    """Reset SGW runtime state (tests only)."""
    global _sgw_status, _sgw_store, _sgw_manager
    stop_sgw_background_refresh()
    _sgw_status = SgwStartupStatusModel()
    _sgw_store = None
    _sgw_manager = None


def set_sgw_startup_success(
    discovered_sg_ids: list[ServiceGroupId],
    store: SgwCacheStore,
    manager: SgwManager,
    last_refresh_epoch: TimestampSec,
) -> None:
    """Record a successful SGW startup outcome."""
    global _sgw_status, _sgw_store, _sgw_manager
    _sgw_store = store
    _sgw_manager = manager
    _sgw_status = SgwStartupStatusModel(
        startup_completed=True,
        discovery_ok=True,
        discovered_sg_ids=list(discovered_sg_ids),
        last_refresh_epoch=TimestampSec(last_refresh_epoch),
        error_message="",
        prime_failed=False,
        guard_restart_count=0,
        last_guard_reason="",
        last_guard_restart_epoch=None,
    )


def set_sgw_startup_failure(error_message: str) -> None:
    """Record a failed SGW startup outcome."""
    global _sgw_status, _sgw_store, _sgw_manager
    _sgw_store = None
    _sgw_manager = None
    trimmed = error_message.strip()
    if trimmed == "":
        trimmed = DEFAULT_SGW_STARTUP_ERROR
    bounded = trimmed[:SGW_LAST_ERROR_MAX_LENGTH]
    _sgw_status = SgwStartupStatusModel(
        startup_completed=True,
        discovery_ok=False,
        discovered_sg_ids=[],
        last_refresh_epoch=None,
        error_message=bounded,
        prime_failed=False,
        guard_restart_count=0,
        last_guard_reason="",
        last_guard_restart_epoch=None,
    )


def set_sgw_startup_prime_failure(
    discovered_sg_ids: list[ServiceGroupId],
    error_message: str,
) -> None:
    """Record a failed SGW priming outcome after successful discovery."""
    global _sgw_status, _sgw_store, _sgw_manager
    _sgw_store = None
    _sgw_manager = None
    trimmed = error_message.strip()
    if trimmed == "":
        trimmed = DEFAULT_SGW_STARTUP_ERROR
    bounded = trimmed[:SGW_LAST_ERROR_MAX_LENGTH]
    _sgw_status = SgwStartupStatusModel(
        startup_completed=True,
        discovery_ok=True,
        discovered_sg_ids=list(discovered_sg_ids),
        last_refresh_epoch=None,
        error_message=bounded,
        prime_failed=True,
        guard_restart_count=0,
        last_guard_reason="",
        last_guard_restart_epoch=None,
    )


def get_sgw_startup_status() -> SgwStartupStatusModel:
    """Return the current SGW startup status."""
    return _sgw_status.model_copy(deep=True)


def get_sgw_store() -> SgwCacheStore | None:
    """Return the active SGW cache store, if available."""
    return _sgw_store


def get_sgw_manager() -> SgwManager | None:
    """Return the active SGW manager, if available."""
    return _sgw_manager


def start_sgw_background_refresh(
    clock: Callable[[], float] | None = None,
) -> bool:
    """Start the SGW background refresh loop if startup succeeded."""
    global _sgw_refresh_thread, _sgw_refresh_running
    status = _sgw_status
    manager = _sgw_manager
    if not status.startup_completed or not status.discovery_ok or status.prime_failed:
        return False
    if manager is None:
        return False
    with _sgw_refresh_lock:
        if _sgw_refresh_thread is not None and _sgw_refresh_thread.is_alive():
            return True
        manager.reset_stop()
        _sgw_refresh_running = True
        _sgw_refresh_thread = threading.Thread(
            target=_run_sgw_refresh_loop,
            name=SGW_REFRESH_THREAD_NAME,
            daemon=True,
            args=(manager, clock),
        )
        _sgw_refresh_thread.start()
    return True


def stop_sgw_background_refresh(
    timeout_seconds: float = DEFAULT_SGW_REFRESH_STOP_TIMEOUT_SECONDS,
) -> None:
    """Stop the SGW background refresh loop if it is running."""
    global _sgw_refresh_thread, _sgw_refresh_running
    manager = _sgw_manager
    if manager is not None:
        manager.stop()
    with _sgw_refresh_lock:
        thread = _sgw_refresh_thread
    if thread is not None:
        thread.join(timeout=float(timeout_seconds))
    with _sgw_refresh_lock:
        if _sgw_refresh_thread is thread and (thread is None or not thread.is_alive()):
            _sgw_refresh_thread = None
            _sgw_refresh_running = False


def is_sgw_refresh_running() -> bool:
    """Return whether the SGW background refresh loop is running."""
    with _sgw_refresh_lock:
        return bool(_sgw_refresh_running)


def _run_sgw_refresh_loop(
    manager: SgwManager,
    clock: Callable[[], float] | None,
) -> None:
    global _sgw_refresh_thread, _sgw_refresh_running
    current_manager = manager
    guard_controller: WorkerGuardController | None = _build_guard_controller(current_manager)
    consecutive_error_cycles = 0
    try:
        while True:
            restart_requested = False

            def _after_cycle(result: object) -> bool:
                nonlocal current_manager, guard_controller, consecutive_error_cycles, restart_requested
                snapshot_time_epoch = _normalize_epoch_seconds(getattr(result, "snapshot_time_epoch", 0.0))
                _record_sgw_refresh_epoch(snapshot_time_epoch)

                errors = list(getattr(result, "errors", []))
                if errors:
                    consecutive_error_cycles += 1
                else:
                    consecutive_error_cycles = 0

                decision = _evaluate_guard_decision(
                    manager=current_manager,
                    controller=guard_controller,
                    now_epoch=snapshot_time_epoch,
                    consecutive_error_cycles=consecutive_error_cycles,
                )
                if decision is None:
                    return False

                restarted_manager = _restart_sgw_runtime_manager(
                    current_manager,
                    snapshot_time_epoch,
                    "; ".join(decision.reasons),
                )
                if restarted_manager is None:
                    return False

                if guard_controller is not None:
                    guard_controller.record_restart()
                current_manager.stop()
                current_manager = restarted_manager
                guard_controller = _build_guard_controller(current_manager)
                consecutive_error_cycles = 0
                restart_requested = True
                return True

            current_manager.refresh_forever(clock=clock, after_cycle=_after_cycle)
            if restart_requested:
                continue
            break
    finally:
        with _sgw_refresh_lock:
            _sgw_refresh_running = False
            _sgw_refresh_thread = None


def _build_guard_controller(manager: SgwManager) -> WorkerGuardController | None:
    settings = manager.get_settings().sgw.guard
    if not bool(settings.enabled):
        return None
    return WorkerGuardController(
        min_restart_interval_seconds=int(settings.min_restart_interval_seconds),
        max_restarts_per_window=int(settings.max_restarts_per_hour),
    )


def _evaluate_guard_decision(
    manager: SgwManager,
    controller: WorkerGuardController | None,
    now_epoch: TimestampSec,
    consecutive_error_cycles: int,
) -> object | None:
    if controller is None:
        return None
    guard_settings = manager.get_settings().sgw.guard
    if not bool(guard_settings.enabled):
        return None
    rss_bytes = read_process_rss_bytes()
    rss_threshold_bytes = None
    if int(guard_settings.rss_restart_threshold_mb) > 0:
        rss_threshold_bytes = int(guard_settings.rss_restart_threshold_mb) * 1024 * 1024
    observation = WorkerGuardObservationModel(
        worker_name="sgw-refresh",
        now_epoch=TimestampSec(now_epoch),
        rss_bytes=rss_bytes,
        consecutive_error_cycles=int(consecutive_error_cycles),
    )
    decision = controller.evaluate(
        observation,
        rss_restart_threshold_bytes=rss_threshold_bytes,
        max_consecutive_error_cycles=int(guard_settings.max_consecutive_error_cycles),
    )
    if not bool(decision.restart_required):
        return None
    return decision


def _restart_sgw_runtime_manager(
    manager: SgwManager,
    now_epoch: TimestampSec,
    reason: str,
) -> SgwManager | None:
    global _sgw_status, _sgw_store, _sgw_manager
    bounded_reason = reason.strip()[:SGW_LAST_ERROR_MAX_LENGTH]
    try:
        new_store = SgwCacheStore()
        restarted_manager = manager.clone_for_restart(store=new_store)
    except Exception:
        return None
    _sgw_store = new_store
    _sgw_manager = restarted_manager
    _sgw_status = _sgw_status.model_copy(
        update={
            "last_refresh_epoch": TimestampSec(now_epoch),
            "guard_restart_count": int(_sgw_status.guard_restart_count) + 1,
            "last_guard_reason": bounded_reason,
            "last_guard_restart_epoch": TimestampSec(now_epoch),
        }
    )
    return restarted_manager


def _record_sgw_refresh_epoch(now_epoch: TimestampSec) -> None:
    """Record the epoch timestamp of the most recent SGW refresh cycle."""
    global _sgw_status
    _sgw_status = _sgw_status.model_copy(update={"last_refresh_epoch": TimestampSec(now_epoch)})


def _normalize_epoch_seconds(value: object) -> TimestampSec:
    """Normalize epoch-like values to whole-second `TimestampSec`."""
    return TimestampSec(int(float(value)))


def compute_sgw_cache_ready(
    discovered_sg_ids: list[ServiceGroupId],
    store: SgwCacheStore | None,
) -> tuple[bool, list[ServiceGroupId]]:
    """Return whether SGW cache is populated for all discovered service groups."""
    if not discovered_sg_ids:
        return (True, [])
    if store is None:
        return (False, list(discovered_sg_ids))
    missing: list[ServiceGroupId] = []
    for sg_id in discovered_sg_ids:
        entry = store.get_entry(sg_id)
        if entry is None or float(entry.snapshot.metadata.snapshot_time_epoch) <= 0:
            missing.append(sg_id)
    return (len(missing) == 0, missing)


__all__ = [
    "SgwStartupStatusModel",
    "compute_sgw_cache_ready",
    "get_sgw_manager",
    "get_sgw_startup_status",
    "get_sgw_store",
    "is_sgw_refresh_running",
    "reset_sgw_runtime_state",
    "start_sgw_background_refresh",
    "stop_sgw_background_refresh",
    "set_sgw_startup_failure",
    "set_sgw_startup_prime_failure",
    "set_sgw_startup_success",
]
