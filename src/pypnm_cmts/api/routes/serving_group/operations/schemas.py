# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pypnm.api.routes.common.service.status_codes import ServiceStatusCode
from pypnm.docsis.data_type.sysDescr import SystemDescriptorModel
from pypnm.lib.types import (
    ChannelId,
    IPv4Str,
    IPv6Str,
    MacAddressStr,
    TimeStamp,
)

from pypnm_cmts.api.common.cmts_reg_status import CmtsCmRegStateModel
from pypnm_cmts.api.common.cmts_request import (
    CmtsRequestEnvelopeModel,
    CmtsServingGroupFilterModel,
)
from pypnm_cmts.docsis.data_type.cmts_cm_reg_state import CmtsCmRegStateText
from pypnm_cmts.lib.constants import CacheRefreshMode
from pypnm_cmts.lib.types import ChSetId, CmtsCmRegState, ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.models import SgwRfChannelModel
from pypnm_cmts.sgw.runtime_state import SgwStartupStatusModel

DEFAULT_PAGE_NUMBER = 1
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
DEFAULT_REFRESH_TIMEOUT_SECONDS = 8
MAX_REFRESH_TIMEOUT_SECONDS = 30
DEFAULT_CHANNEL_SET_ID = ChSetId(0)
DEFAULT_REGISTRATION_STATUS = CmtsCmRegState(1)


class CacheResponseBase(BaseModel):
    """Base response model for cache-backed endpoints."""

    status: ServiceStatusCode = Field(default=ServiceStatusCode.SUCCESS, description="Result status code.")
    message: str = Field(default="", description="Informational or error message.")
    timestamp: TimeStamp = Field(default=TimeStamp(0), description="Unix timestamp in seconds for the response.")


class GetServingGroupIdsRequest(BaseModel):
    """Request model for serving group id retrieval."""

    cmts: CmtsRequestEnvelopeModel | None = Field(default=None, description="Optional CMTS request envelope.")


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


class ServingGroupOnlyEnvelopeModel(BaseModel):
    """CMTS envelope limited to serving group selection."""

    serving_group: CmtsServingGroupFilterModel = Field(default_factory=CmtsServingGroupFilterModel, description="Serving group selection.")


class ServingGroupCacheRefreshRequestModel(BaseModel):
    """Optional refresh controls for cache-backed SG endpoints."""

    mode: CacheRefreshMode = Field(default=CacheRefreshMode.NONE, description="Requested SGW refresh mode.")
    wait_for_cache: bool = Field(default=False, description="Wait for cache snapshot advance before responding.")
    timeout_seconds: int = Field(
        default=DEFAULT_REFRESH_TIMEOUT_SECONDS,
        ge=1,
        le=MAX_REFRESH_TIMEOUT_SECONDS,
        description="Maximum seconds to wait for cache advance when wait_for_cache is true.",
    )

    @model_validator(mode="after")
    def _normalize_wait(self) -> ServingGroupCacheRefreshRequestModel:
        if self.mode == CacheRefreshMode.NONE:
            self.wait_for_cache = False
        return self


class ServingGroupCacheRefreshResultModel(BaseModel):
    """Refresh execution summary for cache-backed SG responses."""

    requested: bool = Field(default=False, description="Whether a refresh mode was requested.")
    mode: CacheRefreshMode = Field(default=CacheRefreshMode.NONE, description="Requested refresh mode.")
    applied: bool = Field(default=False, description="Whether SGW accepted at least one refresh request.")
    wait_for_cache: bool = Field(default=False, description="Whether the endpoint waited for cache advance.")
    advanced: bool = Field(default=False, description="Whether at least one target SG snapshot advanced.")
    timeout_seconds: int = Field(default=DEFAULT_REFRESH_TIMEOUT_SECONDS, ge=1, le=MAX_REFRESH_TIMEOUT_SECONDS, description="Wait timeout used by refresh logic.")
    message: str = Field(default="", description="Refresh informational message.")


class GetServingGroupCableModemsRequest(BaseModel):
    """Request model for serving group cable modem retrieval."""

    model_config = ConfigDict(extra="ignore")

    cmts: ServingGroupOnlyEnvelopeModel = Field(default_factory=ServingGroupOnlyEnvelopeModel, description="Serving group request envelope.")
    refresh: ServingGroupCacheRefreshRequestModel = Field(default_factory=ServingGroupCacheRefreshRequestModel, description="Optional refresh controls.")

    @model_validator(mode="after")
    def _validate_sg_id(self) -> GetServingGroupCableModemsRequest:
        for sg_id in self.cmts.serving_group.id:
            if int(sg_id) <= 0:
                raise ValueError("serving_group.id must be greater than zero.")
        return self


class ServingGroupCableModemEntryModel(BaseModel):
    """Cable modem entry for serving group modem responses."""

    @staticmethod
    def _default_registration_status() -> CmtsCmRegStateModel:
        return CmtsCmRegStateModel(
            status=DEFAULT_REGISTRATION_STATUS,
            text=CmtsCmRegStateText.other,
        )

    mac_address: MacAddressStr = Field(default=MacAddressStr(""), description="Cable modem MAC address.")
    ipv4: IPv4Str = Field(default=IPv4Str(""), description="Cable modem IPv4 address.")
    ipv6: IPv6Str = Field(default=IPv6Str(""), description="Cable modem IPv6 address.")
    sysdescr: SystemDescriptorModel = Field(default_factory=SystemDescriptorModel, description="Cable modem sysDescr model from SGW heavy snapshot.")
    ds_channel_ids: list[ChannelId] = Field(default_factory=list, description="Downstream channel identifiers.")
    us_channel_ids: list[ChannelId] = Field(default_factory=list, description="Upstream channel identifiers.")
    registration_status: CmtsCmRegStateModel = Field(default_factory=_default_registration_status, description="Cable modem registration status.")


class ServingGroupCableModemsGroupModel(BaseModel):
    """Grouped cable modem results for a service group."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    page: int = Field(default=DEFAULT_PAGE_NUMBER, description="Current page number.")
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, description="Requested page size.")
    total_items: int = Field(default=0, description="Total number of modems for the service group.")
    total_pages: int = Field(default=0, description="Total pages for the service group.")
    items: list[ServingGroupCableModemEntryModel] = Field(default_factory=list, description="Paged cable modem entries.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the snapshot.")


class GetServingGroupCableModemsResponse(CacheResponseBase):
    """Response model for serving group cable modem retrieval."""

    requested_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers.")
    resolved_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Resolved service group identifiers.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers not found.")
    refresh: ServingGroupCacheRefreshResultModel = Field(default_factory=ServingGroupCacheRefreshResultModel, description="Refresh execution summary.")
    groups: list[ServingGroupCableModemsGroupModel] = Field(default_factory=list, description="Grouped cable modem entries by service group.")


class GetServingGroupTopologyRequest(BaseModel):
    """Request model for serving group topology retrieval."""

    model_config = ConfigDict(extra="ignore")

    cmts: ServingGroupOnlyEnvelopeModel = Field(default_factory=ServingGroupOnlyEnvelopeModel, description="Serving group request envelope.")

    @model_validator(mode="after")
    def _validate_sg_id(self) -> GetServingGroupTopologyRequest:
        selected = list(self.cmts.serving_group.id)
        if len(selected) > 1:
            raise ValueError("topology requests allow at most one serving_group.id.")
        for sg_id in selected:
            if int(sg_id) <= 0:
                raise ValueError("serving_group.id must be greater than zero for topology requests.")
        return self


class ServingGroupTopologyChannelSetCountModel(BaseModel):
    """Cable modem count per channel set."""

    ch_set_id: ChSetId = Field(..., description="Channel set identifier.")
    modem_count: int = Field(default=0, description="Cable modem count for the channel set.")


class ServingGroupTopologyChannelCountModel(BaseModel):
    """Cable modem count per channel."""

    channel_id: int = Field(default=0, description="Channel identifier.")
    modem_count: int = Field(default=0, description="Cable modem count for the channel.")


class ServingGroupTopologyDownstreamChannelsModel(BaseModel):
    """Downstream RF channel inventory and counts."""

    sc_qam: list[SgwRfChannelModel] = Field(default_factory=list, description="Downstream SC-QAM channel inventory.")
    ofdm: list[SgwRfChannelModel] = Field(default_factory=list, description="Downstream OFDM channel inventory.")
    counts: list[ServingGroupTopologyChannelCountModel] = Field(default_factory=list, description="Cable modem counts per downstream channel.")
    set_counts: list[ServingGroupTopologyChannelSetCountModel] = Field(default_factory=list, description="Cable modem counts per downstream channel set.")


class ServingGroupTopologyUpstreamChannelsModel(BaseModel):
    """Upstream RF channel inventory and counts."""

    sc_qam: list[SgwRfChannelModel] = Field(default_factory=list, description="Upstream SC-QAM channel inventory.")
    ofdma: list[SgwRfChannelModel] = Field(default_factory=list, description="Upstream OFDMA channel inventory.")
    counts: list[ServingGroupTopologyChannelCountModel] = Field(default_factory=list, description="Cable modem counts per upstream channel.")
    set_counts: list[ServingGroupTopologyChannelSetCountModel] = Field(default_factory=list, description="Cable modem counts per upstream channel set.")


class ServingGroupTopologyChannelsModel(BaseModel):
    """Directional RF channel inventory."""

    ds: ServingGroupTopologyDownstreamChannelsModel = Field(default_factory=ServingGroupTopologyDownstreamChannelsModel, description="Downstream channel inventory.")
    us: ServingGroupTopologyUpstreamChannelsModel = Field(default_factory=ServingGroupTopologyUpstreamChannelsModel, description="Upstream channel inventory.")


class ServingGroupTopologyGroupModel(BaseModel):
    """Topology payload for a single service group."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier.")
    ds_ch_set_id: ChSetId = Field(default=DEFAULT_CHANNEL_SET_ID, description="Downstream channel set identifier.")
    us_ch_set_id: ChSetId = Field(default=DEFAULT_CHANNEL_SET_ID, description="Upstream channel set identifier.")
    channels: ServingGroupTopologyChannelsModel = Field(default_factory=ServingGroupTopologyChannelsModel, description="Directional channel inventory and counts.")
    page: int = Field(default=DEFAULT_PAGE_NUMBER, description="Current page number.")
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, description="Requested page size.")
    total_items: int = Field(default=0, description="Total number of modems for the service group.")
    total_pages: int = Field(default=0, description="Total pages for the service group.")
    modems: list[MacAddressStr] = Field(default_factory=list, description="Paged cable modem MAC addresses.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the snapshot.")


class GetServingGroupTopologyResponse(CacheResponseBase):
    """Response model for serving group topology retrieval."""

    requested_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers.")
    resolved_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Resolved service group identifiers.")
    missing_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Requested service group identifiers not found.")
    groups: list[ServingGroupTopologyGroupModel] = Field(default_factory=list, description="Grouped topology entries by service group.")


__all__ = [
    "CacheResponseBase",
    "DEFAULT_PAGE_NUMBER",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "GetServingGroupIdsRequest",
    "GetServingGroupIdsResponse",
    "ServingGroupStatusResponse",
    "ServingGroupOnlyEnvelopeModel",
    "GetServingGroupCableModemsRequest",
    "GetServingGroupCableModemsResponse",
    "ServingGroupCacheRefreshRequestModel",
    "ServingGroupCacheRefreshResultModel",
    "ServingGroupCableModemEntryModel",
    "ServingGroupCableModemsGroupModel",
    "GetServingGroupTopologyRequest",
    "GetServingGroupTopologyResponse",
    "ServingGroupCacheSummaryModel",
    "ServingGroupTopologyChannelCountModel",
    "ServingGroupTopologyChannelSetCountModel",
    "ServingGroupTopologyChannelsModel",
    "ServingGroupTopologyDownstreamChannelsModel",
    "ServingGroupTopologyGroupModel",
    "ServingGroupTopologyUpstreamChannelsModel",
]
