# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, Field, model_serializer
from pypnm.lib.types import IPv4Str, IPv6Str, MacAddressStr

from pypnm_cmts.lib.constants import RfChannelType
from pypnm_cmts.lib.types import ChSetId, CmtsCmRegState, ServiceGroupId
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


class SgwRfChannelModel(BaseModel):
    """RF channel inventory entry for SGW snapshots."""

    channel_id: int = Field(default=0, description="Channel identifier.")
    channel_type: RfChannelType = Field(default=RfChannelType.SC_QAM, description="Channel modulation type.")
    center_frequency_hz: int | None = Field(default=None, description="Channel center frequency (Hz).")
    start_frequency_hz: int | None = Field(default=None, description="Channel start frequency (Hz).")
    plc_frequency_hz: int | None = Field(default=None, description="OFDM PLC frequency (Hz).")
    channel_width_hz: int | None = Field(default=None, description="Channel width (Hz).")
    lower_frequency_hz: int | None = Field(default=None, description="Lower boundary frequency (Hz).")
    upper_frequency_hz: int | None = Field(default=None, description="Upper boundary frequency (Hz).")

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Callable[[SgwRfChannelModel], dict[str, object]]) -> dict[str, object]:
        data = handler(self)
        if self.channel_type == RfChannelType.SC_QAM:
            data.pop("start_frequency_hz", None)
            data.pop("plc_frequency_hz", None)
            return data
        if self.channel_type == RfChannelType.OFDM:
            data.pop("center_frequency_hz", None)
            data.pop("start_frequency_hz", None)
            return data
        if self.channel_type == RfChannelType.OFDMA:
            data.pop("center_frequency_hz", None)
            data.pop("start_frequency_hz", None)
            data.pop("plc_frequency_hz", None)
        return data


class SgwHeavyInventoryModel(BaseModel):
    """Heavy refresh inventory payload prior to snapshot normalization."""

    ds_ch_set_id: ChSetId = Field(default=ChSetId(0), description="Downstream channel set identifier.")
    us_ch_set_id: ChSetId = Field(default=ChSetId(0), description="Upstream channel set identifier.")
    ds_channel_ids: list[int] = Field(default_factory=list, description="Downstream channel identifiers.")
    us_channel_ids: list[int] = Field(default_factory=list, description="Upstream channel identifiers.")
    ds_rf_channels: list[SgwRfChannelModel] = Field(default_factory=list, description="Downstream RF channel inventory.")
    us_rf_channels: list[SgwRfChannelModel] = Field(default_factory=list, description="Upstream RF channel inventory.")
    cable_modems: list[SgwCableModemModel] = Field(default_factory=list, description="Cable modem membership list.")


class SgwCableModemModel(BaseModel):
    """Minimal cable modem identity for SGW snapshots."""

    mac: MacAddressStr = Field(default=MacAddressStr(""), description="Cable modem MAC address.")
    ipv4: IPv4Str = Field(default=IPv4Str(""), description="Cable modem IPv4 address.")
    ipv6: IPv6Str = Field(default=IPv6Str(""), description="Cable modem IPv6 address.")
    ds_channel_set: ChSetId = Field(default=ChSetId(0), description="Downstream channel set id.")
    us_channel_set: ChSetId = Field(default=ChSetId(0), description="Upstream channel set id.")
    registration_status: CmtsCmRegState = Field(default=CmtsCmRegState(1), description="Cable modem registration status.")


class SgwSnapshotModel(BaseModel):
    """Snapshot payload for a service group cache entry."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier for the snapshot.")
    ds_ch_set_id: ChSetId = Field(default=ChSetId(0), description="Downstream channel set identifier.")
    us_ch_set_id: ChSetId = Field(default=ChSetId(0), description="Upstream channel set identifier.")
    ds_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Downstream channel summary.")
    us_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Upstream channel summary.")
    ds_rf_channels: list[SgwRfChannelModel] = Field(default_factory=list, description="Downstream RF channel inventory.")
    us_rf_channels: list[SgwRfChannelModel] = Field(default_factory=list, description="Upstream RF channel inventory.")
    cable_modems: list[SgwCableModemModel] = Field(default_factory=list, description="Cable modem membership list.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the snapshot.")


class SgwSnapshotPayloadModel(BaseModel):
    """Snapshot payload components from a heavy refresh."""

    ds_ch_set_id: ChSetId = Field(default=ChSetId(0), description="Downstream channel set identifier.")
    us_ch_set_id: ChSetId = Field(default=ChSetId(0), description="Upstream channel set identifier.")
    ds_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Downstream channel summary.")
    us_channels: SgwChannelSummaryModel = Field(default_factory=SgwChannelSummaryModel, description="Upstream channel summary.")
    ds_rf_channels: list[SgwRfChannelModel] = Field(default_factory=list, description="Downstream RF channel inventory.")
    us_rf_channels: list[SgwRfChannelModel] = Field(default_factory=list, description="Upstream RF channel inventory.")
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
    "SgwHeavyInventoryModel",
    "SgwRfChannelModel",
    "SgwSnapshotModel",
    "SgwSnapshotPayloadModel",
    "SgwRefreshErrorModel",
    "SgwRefreshResultModel",
]
