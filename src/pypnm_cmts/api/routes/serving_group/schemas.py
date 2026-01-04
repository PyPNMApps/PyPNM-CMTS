# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode

from pypnm_cmts.lib.constants import CacheRefreshMode
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.models import SgwCableModemModel, SgwChannelSummaryModel
from pypnm_cmts.sgw.runtime_state import SgwStartupStatusModel

DEFAULT_PAGE_NUMBER = 1
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
DEFAULT_REFRESH_MODE = CacheRefreshMode.NONE
DEFAULT_MAX_WAIT_SECONDS = 0.0
MAX_WAIT_SECONDS = 10.0
DEFAULT_TOPOLOGY_SG_ID = ServiceGroupId(0)


class CacheResponseBase(BaseModel):
    """Base response model for cache-backed endpoints."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Result status code.")
    message: str = Field(default="", description="Informational or error message.")
    timestamp: str = Field(default="", description="ISO-8601 timestamp for the response.")


class GetServingGroupIdsRequest(BaseModel):
    """Request model for serving group id retrieval."""


class ServingGroupCacheSummaryModel(BaseModel):
    """Cache summary for a serving group snapshot."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    metadata: SgwCacheMetadataModel | None = Field(default=None, description="Cache metadata for the snapshot.")


class GetServingGroupIdsResponse(CacheResponseBase):
    """Response model for serving group id retrieval."""

    discovered_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Discovered service group identifiers.")
    sgw_ready: bool = Field(default=False, description="Whether SGW cache is primed for all discovered SGs.")
    summaries: list[ServingGroupCacheSummaryModel] = Field(default_factory=list, description="Per-SG cache summary entries.")


class ServingGroupStatusResponse(CacheResponseBase):
    """Response model for serving group cache and runtime status."""

    startup_status: SgwStartupStatusModel = Field(default_factory=SgwStartupStatusModel, description="SGW startup status snapshot.")
    refresh_running: bool = Field(default=False, description="Whether the SGW background refresh loop is running.")
    discovered_count: int = Field(default=0, description="Count of discovered service groups.")
    cache_ready: bool = Field(default=False, description="Whether SGW cache is primed for all discovered SGs.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service group identifiers missing cache snapshots.")


class GetServingGroupCableModemsRequest(BaseModel):
    """Request model for serving group cable modem retrieval."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    page: int = Field(default=DEFAULT_PAGE_NUMBER, ge=1, description="Page number (1-based).")
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page.")
    refresh: CacheRefreshMode = Field(default=DEFAULT_REFRESH_MODE, description="Optional refresh mode for the request.")
    max_wait_seconds: float = Field(default=DEFAULT_MAX_WAIT_SECONDS, ge=0.0, le=MAX_WAIT_SECONDS, description="Maximum time to wait for a refresh.")
    require_fresh: bool = Field(default=False, description="Wait for a refreshed snapshot when refresh is requested.")

    @model_validator(mode="after")
    def _validate_sg_id(self) -> GetServingGroupCableModemsRequest:
        if int(self.sg_id) < 0:
            raise ValueError("sg_id must be zero or greater.")
        return self


class GetServingGroupCableModemsResponse(CacheResponseBase):
    """Response model for serving group cable modem retrieval."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service group identifiers included in aggregation.")
    page: int = Field(default=DEFAULT_PAGE_NUMBER, description="Current page number.")
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, description="Requested page size.")
    total_count: int = Field(default=0, description="Total number of cable modems for the service group.")
    items: list[SgwCableModemModel] = Field(default_factory=list, description="Paged cable modem entries.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the snapshot.")
    refresh_applied: bool = Field(default=False, description="Whether a refresh request was accepted for processing.")
    waited_seconds: float = Field(default=0.0, description="Seconds waited for a refresh to advance.")


class GetServingGroupTopologyRequest(BaseModel):
    """Request model for serving group topology retrieval."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    refresh: CacheRefreshMode = Field(default=DEFAULT_REFRESH_MODE, description="Optional refresh mode for the request.")
    max_wait_seconds: float = Field(default=DEFAULT_MAX_WAIT_SECONDS, ge=0.0, le=MAX_WAIT_SECONDS, description="Maximum time to wait for a refresh.")
    require_fresh: bool = Field(default=False, description="Wait for a refreshed snapshot when refresh is requested.")

    @model_validator(mode="after")
    def _validate_sg_id(self) -> GetServingGroupTopologyRequest:
        if int(self.sg_id) < 0:
            raise ValueError("sg_id must be zero or greater.")
        return self


class ServingGroupTopologyModel(BaseModel):
    """Topology summary payload for a serving group."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    ds_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Downstream channel summary.")
    us_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Upstream channel summary.")


class GetServingGroupTopologyResponse(CacheResponseBase):
    """Response model for serving group topology retrieval."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service group identifiers included in aggregation.")
    topology: ServingGroupTopologyModel = Field(default_factory=lambda: ServingGroupTopologyModel(sg_id=DEFAULT_TOPOLOGY_SG_ID), description="Cached topology summary.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the snapshot.")
    refresh_applied: bool = Field(default=False, description="Whether a refresh request was accepted for processing.")
    waited_seconds: float = Field(default=0.0, description="Seconds waited for a refresh to advance.")


__all__ = [
    "CacheResponseBase",
    "DEFAULT_PAGE_NUMBER",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_REFRESH_MODE",
    "DEFAULT_MAX_WAIT_SECONDS",
    "DEFAULT_TOPOLOGY_SG_ID",
    "MAX_PAGE_SIZE",
    "MAX_WAIT_SECONDS",
    "GetServingGroupIdsRequest",
    "GetServingGroupIdsResponse",
    "ServingGroupStatusResponse",
    "GetServingGroupCableModemsRequest",
    "GetServingGroupCableModemsResponse",
    "GetServingGroupTopologyRequest",
    "GetServingGroupTopologyResponse",
    "ServingGroupCacheSummaryModel",
    "ServingGroupTopologyModel",
]
