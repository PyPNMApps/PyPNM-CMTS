# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import threading
from collections.abc import Callable

from pydantic import BaseModel, Field

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SGW_LAST_ERROR_MAX_LENGTH
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.store import SgwCacheStore

DEFAULT_SGW_STARTUP_ERROR = "sgw startup failed"
DEFAULT_SGW_REFRESH_STOP_TIMEOUT_SECONDS = 5.0
SGW_REFRESH_THREAD_NAME = "pypnm-cmts-sgw-refresh"


class SgwStartupStatusModel(BaseModel):
    """Runtime startup status for SGW discovery and priming."""

    startup_completed: bool = Field(default=False, description="Whether SGW startup has completed.")
    discovery_ok: bool = Field(default=False, description="Whether SG discovery completed successfully.")
    discovered_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Discovered service group identifiers.")
    last_refresh_epoch: float | None = Field(default=None, ge=0.0, description="Epoch timestamp for the last SGW refresh.")
    error_message: str = Field(default="", max_length=SGW_LAST_ERROR_MAX_LENGTH, description="Bounded startup error message.")
    prime_failed: bool = Field(default=False, description="Whether SGW priming failed after discovery.")


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
    last_refresh_epoch: float,
) -> None:
    """Record a successful SGW startup outcome."""
    global _sgw_status, _sgw_store, _sgw_manager
    _sgw_store = store
    _sgw_manager = manager
    _sgw_status = SgwStartupStatusModel(
        startup_completed=True,
        discovery_ok=True,
        discovered_sg_ids=list(discovered_sg_ids),
        last_refresh_epoch=float(last_refresh_epoch),
        error_message="",
        prime_failed=False,
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
    try:
        manager.refresh_forever(clock=clock)
    finally:
        with _sgw_refresh_lock:
            _sgw_refresh_running = False
            _sgw_refresh_thread = None


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
