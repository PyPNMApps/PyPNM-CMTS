# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import random
from collections.abc import Callable

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel, SgwRefreshState
from pypnm_cmts.sgw.models import (
    DEFAULT_AGE_SECONDS,
    SgwCacheEntryModel,
    SgwRefreshErrorModel,
    SgwRefreshResultModel,
)
from pypnm_cmts.sgw.store import SgwCacheStore

JITTER_MIN_SECONDS = 0


class SgwManager:
    """Serving group worker cache manager."""

    def __init__(
        self,
        settings: CmtsOrchestratorSettings,
        store: SgwCacheStore | None = None,
        service_groups: list[ServiceGroupId] | None = None,
        jitter_provider: Callable[[ServiceGroupId, int], int] | None = None,
    ) -> None:
        """
        Initialize the SGW manager.

        Args:
            settings (CmtsOrchestratorSettings): Orchestrator settings instance.
            store (SgwCacheStore | None): Optional cache store.
            service_groups (list[ServiceGroupId] | None): Initial service group identifiers.
            jitter_provider (Callable[[ServiceGroupId, int], int] | None): Optional jitter provider.
        """
        self._settings = settings
        self._store = store if store is not None else SgwCacheStore()
        self._service_groups = list(service_groups) if service_groups is not None else []
        self._jitter_provider = jitter_provider if jitter_provider is not None else self._default_jitter

    def set_service_groups(self, service_groups: list[ServiceGroupId]) -> None:
        """Update the service groups managed by this instance."""
        self._service_groups = list(service_groups)

    def refresh_once(self, now_epoch: float) -> SgwRefreshResultModel:
        """
        Execute a single refresh cycle.

        Args:
            now_epoch (float): Current time in epoch seconds.

        Returns:
            SgwRefreshResultModel: Summary of refresh operations performed.
        """
        if float(now_epoch) < 0:
            raise ValueError("now_epoch must be non-negative.")
        if not bool(self._settings.sgw.enabled):
            return SgwRefreshResultModel(snapshot_time_epoch=float(now_epoch))

        heavy_refreshed: list[ServiceGroupId] = []
        light_refreshed: list[ServiceGroupId] = []
        errors: list[SgwRefreshErrorModel] = []

        for sg_id in list(self._service_groups):
            entry = self._ensure_entry(sg_id, now_epoch)
            metadata = entry.metadata
            jitter_seconds = self._resolve_jitter_seconds(sg_id)

            try:
                heavy_due = self._is_refresh_due(
                    metadata.last_heavy_refresh_epoch,
                    int(self._settings.sgw.poll_heavy_seconds),
                    jitter_seconds,
                    now_epoch,
                )
                if heavy_due:
                    self._refresh_heavy(sg_id, now_epoch)
                    heavy_refreshed.append(sg_id)
                    light_refreshed.append(sg_id)
                else:
                    light_due = self._is_refresh_due(
                        metadata.last_light_refresh_epoch,
                        int(self._settings.sgw.poll_light_seconds),
                        jitter_seconds,
                        now_epoch,
                    )
                    if light_due:
                        self._refresh_light(sg_id, now_epoch)
                        light_refreshed.append(sg_id)
            except Exception as exc:
                metadata = self._store.mark_error(sg_id, str(exc), now_epoch)
                errors.append(SgwRefreshErrorModel(sg_id=sg_id, message=metadata.last_error or ""))

            entry = self._store.get_entry(sg_id) or entry
            metadata = entry.metadata
            age_seconds = max(DEFAULT_AGE_SECONDS, float(now_epoch) - float(metadata.snapshot_time_epoch))
            metadata = metadata.model_copy(update={"age_seconds": age_seconds})

            if metadata.refresh_state != SgwRefreshState.ERROR:
                if self._store.compute_staleness(age_seconds, int(self._settings.sgw.cache_max_age_seconds)):
                    metadata = metadata.model_copy(update={"refresh_state": SgwRefreshState.STALE})
                else:
                    metadata = metadata.model_copy(update={"refresh_state": SgwRefreshState.OK})

            entry.metadata = metadata
            self._store.upsert_entry(entry)

        return SgwRefreshResultModel(
            snapshot_time_epoch=float(now_epoch),
            heavy_refreshed_sg_ids=heavy_refreshed,
            light_refreshed_sg_ids=light_refreshed,
            errors=errors,
        )

    def _ensure_entry(self, sg_id: ServiceGroupId, now_epoch: float) -> SgwCacheEntryModel:
        entry = self._store.get_entry(sg_id)
        if entry is not None:
            return entry
        metadata = SgwCacheMetadataModel(
            snapshot_time_epoch=float(now_epoch),
            age_seconds=DEFAULT_AGE_SECONDS,
        )
        entry = SgwCacheEntryModel(sg_id=sg_id, metadata=metadata)
        self._store.upsert_entry(entry)
        return entry

    def _refresh_heavy(self, sg_id: ServiceGroupId, now_epoch: float) -> None:
        entry = self._ensure_entry(sg_id, now_epoch)
        metadata = entry.metadata.model_copy(
            update={
                "snapshot_time_epoch": float(now_epoch),
                "age_seconds": DEFAULT_AGE_SECONDS,
                "last_heavy_refresh_epoch": float(now_epoch),
                "last_light_refresh_epoch": float(now_epoch),
                "refresh_state": SgwRefreshState.OK,
                "last_error": None,
            }
        )
        entry.metadata = metadata
        self._store.upsert_entry(entry)

    def _refresh_light(self, sg_id: ServiceGroupId, now_epoch: float) -> None:
        entry = self._ensure_entry(sg_id, now_epoch)
        metadata = entry.metadata.model_copy(
            update={
                "snapshot_time_epoch": float(now_epoch),
                "age_seconds": DEFAULT_AGE_SECONDS,
                "last_light_refresh_epoch": float(now_epoch),
                "refresh_state": SgwRefreshState.OK,
                "last_error": None,
            }
        )
        entry.metadata = metadata
        self._store.upsert_entry(entry)

    def _is_refresh_due(
        self,
        last_refresh_epoch: float | None,
        interval_seconds: int,
        jitter_seconds: int,
        now_epoch: float,
    ) -> bool:
        if last_refresh_epoch is None:
            return True
        elapsed = float(now_epoch) - float(last_refresh_epoch)
        return elapsed >= float(interval_seconds + jitter_seconds)

    def _resolve_jitter_seconds(self, sg_id: ServiceGroupId) -> int:
        max_jitter = int(self._settings.sgw.refresh_jitter_seconds)
        if max_jitter <= 0:
            return JITTER_MIN_SECONDS
        jitter_value = int(self._jitter_provider(sg_id, max_jitter))
        if jitter_value < JITTER_MIN_SECONDS:
            return JITTER_MIN_SECONDS
        if jitter_value > max_jitter:
            return max_jitter
        return jitter_value

    @staticmethod
    def _default_jitter(_sg_id: ServiceGroupId, max_jitter_seconds: int) -> int:
        if max_jitter_seconds <= 0:
            return JITTER_MIN_SECONDS
        return random.randint(JITTER_MIN_SECONDS, max_jitter_seconds)


__all__ = [
    "SgwManager",
]
