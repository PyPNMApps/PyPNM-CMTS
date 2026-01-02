# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SGW_LAST_ERROR_MAX_LENGTH
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.store import SgwCacheStore

DEFAULT_SGW_STARTUP_ERROR = "sgw startup failed"


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


def reset_sgw_runtime_state() -> None:
    """Reset SGW runtime state (tests only)."""
    global _sgw_status, _sgw_store, _sgw_manager
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
    "reset_sgw_runtime_state",
    "set_sgw_startup_failure",
    "set_sgw_startup_prime_failure",
    "set_sgw_startup_success",
]
