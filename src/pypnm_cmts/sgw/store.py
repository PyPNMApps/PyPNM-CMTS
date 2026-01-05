# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import threading

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)
from pypnm_cmts.sgw.models import (
    DEFAULT_AGE_SECONDS,
    SgwCacheEntryModel,
    SgwSnapshotModel,
)


class SgwCacheStore:
    """In-memory cache store for SGW entries."""

    def __init__(self) -> None:
        self._entries: dict[ServiceGroupId, SgwCacheEntryModel] = {}
        self._lock = threading.Lock()

    def get_ids(self) -> list[ServiceGroupId]:
        """Return the cached service group identifiers."""
        with self._lock:
            return sorted(self._entries.keys(), key=int)

    def get_entry(self, sg_id: ServiceGroupId) -> SgwCacheEntryModel | None:
        """Return the cache entry for the service group if present."""
        with self._lock:
            entry = self._entries.get(sg_id)
            if entry is None:
                return None
            return entry.model_copy(deep=True)

    def upsert_entry(self, entry: SgwCacheEntryModel) -> None:
        """Insert or replace a cache entry."""
        with self._lock:
            self._entries[entry.sg_id] = entry.model_copy(deep=True)

    def update_metadata(self, sg_id: ServiceGroupId, metadata: SgwCacheMetadataModel) -> None:
        """Update or create metadata for a service group entry."""
        with self._lock:
            entry = self._entries.get(sg_id)
            if entry is None:
                snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
                new_entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)
                self._entries[sg_id] = new_entry.model_copy(deep=True)
                return
            snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
            new_entry = entry.model_copy(update={"snapshot": snapshot})
            self._entries[sg_id] = new_entry.model_copy(deep=True)

    def mark_error(self, sg_id: ServiceGroupId, error_message: str, now_epoch: float) -> SgwCacheMetadataModel:
        """Mark a cache entry as errored and update its metadata."""
        with self._lock:
            entry = self._entries.get(sg_id)
            if entry is None:
                snapshot = SgwSnapshotModel(sg_id=sg_id)
                entry = SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot)

            trimmed = self._normalize_error_message(error_message)
            metadata = entry.snapshot.metadata.model_copy(
                update={
                    "snapshot_time_epoch": float(now_epoch),
                    "age_seconds": DEFAULT_AGE_SECONDS,
                    "refresh_state": SgwRefreshState.ERROR,
                    "last_error": trimmed,
                }
            )
            snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
            new_entry = entry.model_copy(update={"snapshot": snapshot})
            self._entries[sg_id] = new_entry.model_copy(deep=True)
            return metadata

    @staticmethod
    def _normalize_error_message(message: str) -> str:
        trimmed = message.strip()
        if trimmed == "":
            return ""
        return trimmed[:SGW_LAST_ERROR_MAX_LENGTH]

    @staticmethod
    def compute_staleness(age_seconds: float, cache_max_age_seconds: int) -> bool:
        """Return whether the cache entry should be considered stale."""
        return float(age_seconds) >= float(cache_max_age_seconds)


__all__ = [
    "SgwCacheStore",
]
