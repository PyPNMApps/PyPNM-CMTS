# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from datetime import datetime, timezone

from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.api.routes.serving_group.schemas import (
    GetServingGroupCableModemsRequest,
    GetServingGroupCableModemsResponse,
    GetServingGroupIdsResponse,
    GetServingGroupTopologyRequest,
    GetServingGroupTopologyResponse,
    ServingGroupCacheSummaryModel,
    ServingGroupTopologyModel,
)
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
    SgwRefreshState,
)
from pypnm_cmts.sgw.models import SgwCableModemModel
from pypnm_cmts.sgw.runtime_state import (
    compute_sgw_cache_ready,
    get_sgw_startup_status,
    get_sgw_store,
)
from pypnm_cmts.sgw.store import SgwCacheStore


class ServingGroupCacheService:
    """Service layer for cache-backed serving group endpoints."""

    STORE_UNAVAILABLE_MESSAGE = "sgw store not available"
    SNAPSHOT_MISSING_TEMPLATE = "sgw snapshot missing for sg_id={sg_id}"

    def get_ids(self) -> GetServingGroupIdsResponse:
        """Return discovered service group identifiers and cache summaries."""
        status = get_sgw_startup_status()
        discovered_sg_ids = list(status.discovered_sg_ids)
        store = get_sgw_store()
        sgw_ready, _missing = compute_sgw_cache_ready(discovered_sg_ids, store)
        summaries: list[ServingGroupCacheSummaryModel] = []
        now_epoch = self._now_epoch()
        for sg_id in discovered_sg_ids:
            metadata = self._resolve_metadata(sg_id, store, now_epoch)
            summaries.append(ServingGroupCacheSummaryModel(sg_id=sg_id, metadata=metadata))
        message = "" if sgw_ready else "sgw cache not ready"
        return GetServingGroupIdsResponse(
            status=ServiceStatusCode.SUCCESS,
            message=message,
            timestamp=self._utc_now(),
            discovered_sg_ids=discovered_sg_ids,
            sgw_ready=sgw_ready,
            summaries=summaries,
        )

    def get_cable_modems(
        self,
        request: GetServingGroupCableModemsRequest,
    ) -> GetServingGroupCableModemsResponse:
        """Return paged cable modem membership for a service group."""
        sg_id = request.sg_id
        store = get_sgw_store()
        entry = store.get_entry(sg_id) if store is not None else None
        now_epoch = self._now_epoch()
        metadata = self._resolve_metadata(sg_id, store, now_epoch)
        if entry is None:
            return GetServingGroupCableModemsResponse(
                status=ServiceStatusCode.FAILURE,
                message=f"sgw snapshot not available for sg_id={int(sg_id)}",
                timestamp=self._utc_now(),
                sg_id=sg_id,
                page=request.page,
                page_size=request.page_size,
                total_count=0,
                items=[],
                metadata=metadata,
            )

        items = self._paginate_modems(entry.snapshot.cable_modems, request.page, request.page_size)
        total_count = len(entry.snapshot.cable_modems)
        return GetServingGroupCableModemsResponse(
            status=ServiceStatusCode.SUCCESS,
            message="",
            timestamp=self._utc_now(),
            sg_id=sg_id,
            page=request.page,
            page_size=request.page_size,
            total_count=total_count,
            items=items,
            metadata=metadata,
        )

    def get_topology(
        self,
        request: GetServingGroupTopologyRequest,
    ) -> GetServingGroupTopologyResponse:
        """Return cached topology summary for a service group."""
        sg_id = request.sg_id
        store = get_sgw_store()
        entry = store.get_entry(sg_id) if store is not None else None
        now_epoch = self._now_epoch()
        metadata = self._resolve_metadata(sg_id, store, now_epoch)
        if entry is None:
            topology = ServingGroupTopologyModel(sg_id=sg_id)
            return GetServingGroupTopologyResponse(
                status=ServiceStatusCode.FAILURE,
                message=f"sgw snapshot not available for sg_id={int(sg_id)}",
                timestamp=self._utc_now(),
                sg_id=sg_id,
                topology=topology,
                metadata=metadata,
            )

        topology = ServingGroupTopologyModel(
            sg_id=sg_id,
            ds_channels=entry.snapshot.ds_channels,
            us_channels=entry.snapshot.us_channels,
        )
        return GetServingGroupTopologyResponse(
            status=ServiceStatusCode.SUCCESS,
            message="",
            timestamp=self._utc_now(),
            sg_id=sg_id,
            topology=topology,
            metadata=metadata,
        )

    def _resolve_metadata(
        self,
        sg_id: ServiceGroupId,
        store: SgwCacheStore | None,
        now_epoch: float,
    ) -> SgwCacheMetadataModel:
        if store is None:
            return self._build_error_metadata(self.STORE_UNAVAILABLE_MESSAGE)
        entry = store.get_entry(sg_id)
        if entry is None:
            message = self.SNAPSHOT_MISSING_TEMPLATE.format(sg_id=int(sg_id))
            return self._build_error_metadata(message)
        metadata = entry.snapshot.metadata
        snapshot_epoch = float(metadata.snapshot_time_epoch)
        if snapshot_epoch <= 0:
            return metadata
        age_seconds = max(0.0, float(now_epoch) - snapshot_epoch)
        return metadata.model_copy(update={"age_seconds": age_seconds})

    @staticmethod
    def _paginate_modems(
        modems: list[SgwCableModemModel],
        page: int,
        page_size: int,
    ) -> list[SgwCableModemModel]:
        ordered = sorted(modems, key=lambda modem: str(modem.mac))
        start = (int(page) - 1) * int(page_size)
        end = start + int(page_size)
        if start >= len(ordered):
            return []
        return ordered[start:end]

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _now_epoch() -> float:
        return datetime.now(timezone.utc).timestamp()

    @staticmethod
    def _build_error_metadata(message: str) -> SgwCacheMetadataModel:
        bounded = message[:SGW_LAST_ERROR_MAX_LENGTH]
        return SgwCacheMetadataModel(
            snapshot_time_epoch=0.0,
            refresh_state=SgwRefreshState.ERROR,
            last_error=bounded,
        )


__all__ = [
    "ServingGroupCacheService",
]
