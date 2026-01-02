# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)
from pypnm_cmts.sgw.models import DEFAULT_AGE_SECONDS, SgwCacheEntryModel


class SgwCacheStore:
    """In-memory cache store for SGW entries."""

    def __init__(self) -> None:
        self._entries: dict[ServiceGroupId, SgwCacheEntryModel] = {}

    def get_ids(self) -> list[ServiceGroupId]:
        """Return the cached service group identifiers."""
        return sorted(self._entries.keys(), key=int)

    def get_entry(self, sg_id: ServiceGroupId) -> SgwCacheEntryModel | None:
        """Return the cache entry for the service group if present."""
        return self._entries.get(sg_id)

    def upsert_entry(self, entry: SgwCacheEntryModel) -> None:
        """Insert or replace a cache entry."""
        self._entries[entry.sg_id] = entry

    def update_metadata(self, sg_id: ServiceGroupId, metadata: SgwCacheMetadataModel) -> None:
        """Update or create metadata for a service group entry."""
        entry = self._entries.get(sg_id)
        if entry is None:
            self._entries[sg_id] = SgwCacheEntryModel(sg_id=sg_id, metadata=metadata)
            return
        entry.metadata = metadata

    def mark_error(self, sg_id: ServiceGroupId, error_message: str, now_epoch: float) -> SgwCacheMetadataModel:
        """Mark a cache entry as errored and update its metadata."""
        entry = self._entries.get(sg_id)
        if entry is None:
            entry = SgwCacheEntryModel(sg_id=sg_id)
            self._entries[sg_id] = entry

        trimmed = error_message[:SGW_LAST_ERROR_MAX_LENGTH]
        metadata = entry.metadata.model_copy(
            update={
                "snapshot_time_epoch": float(now_epoch),
                "age_seconds": DEFAULT_AGE_SECONDS,
                "refresh_state": SgwRefreshState.ERROR,
                "last_error": trimmed,
            }
        )
        entry.metadata = metadata
        return metadata

    @staticmethod
    def compute_staleness(age_seconds: float, cache_max_age_seconds: int) -> bool:
        """Return whether the cache entry should be considered stale."""
        return float(age_seconds) >= float(cache_max_age_seconds)


__all__ = [
    "SgwCacheStore",
]
