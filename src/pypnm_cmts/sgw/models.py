# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field
from pypnm.lib.types import IPv4Str, IPv6Str, MacAddressStr

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
)

DEFAULT_AGE_SECONDS = 0.0
DEFAULT_CHANNEL_COUNT = 0


class SgwChannelSummaryModel(BaseModel):
    """Summary of channel inventory for a service group."""

    count: int = Field(default=DEFAULT_CHANNEL_COUNT, description="Number of channels in the summary.")
    channel_ids: list[int] = Field(default_factory=list, description="Channel identifiers in the summary.")


class SgwCableModemModel(BaseModel):
    """Minimal cable modem identity for SGW snapshots."""

    mac: MacAddressStr = Field(default=MacAddressStr(""), description="Cable modem MAC address.")
    ipv4: IPv4Str = Field(default=IPv4Str(""), description="Cable modem IPv4 address.")
    ipv6: IPv6Str = Field(default=IPv6Str(""), description="Cable modem IPv6 address.")


class SgwSnapshotModel(BaseModel):
    """Snapshot payload for a service group cache entry."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier for the snapshot.")
    ds_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Downstream channel summary.")
    us_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Upstream channel summary.")
    cable_modems: list[SgwCableModemModel] = Field(default_factory=list, description="Cable modem membership list.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the snapshot.")


class SgwSnapshotPayloadModel(BaseModel):
    """Snapshot payload components from a heavy refresh."""

    ds_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Downstream channel summary.")
    us_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Upstream channel summary.")
    cable_modems: list[SgwCableModemModel] = Field(default_factory=list, description="Cable modem membership list.")


class SgwCacheEntryModel(BaseModel):
    """Cache entry for serving group worker data."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier for the cache entry.")
    snapshot: SgwSnapshotModel = Field(..., description="Snapshot payload for the cache entry.")


class SgwRefreshErrorModel(BaseModel):
    """Error detail captured during a refresh attempt."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier that failed to refresh.")
    message: str = Field(default="", max_length=SGW_LAST_ERROR_MAX_LENGTH, description="Bounded refresh error message.")


class SgwRefreshResultModel(BaseModel):
    """Result summary for a single refresh cycle."""

    snapshot_time_epoch: float = Field(default=0.0, ge=0.0, description="Snapshot timestamp in epoch seconds.")
    heavy_refreshed_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups refreshed via heavy refresh.")
    light_refreshed_sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service groups refreshed via light refresh.")
    errors: list[SgwRefreshErrorModel] = Field(default_factory=list, description="Errors captured during refresh.")


__all__ = [
    "SgwCacheEntryModel",
    "SgwCableModemModel",
    "SgwChannelSummaryModel",
    "SgwSnapshotModel",
    "SgwSnapshotPayloadModel",
    "SgwRefreshErrorModel",
    "SgwRefreshResultModel",
]
