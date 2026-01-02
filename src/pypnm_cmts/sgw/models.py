# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field

from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import (
    SGW_LAST_ERROR_MAX_LENGTH,
    SgwCacheMetadataModel,
)

JsonScalar = str | int | float | bool | None
DEFAULT_AGE_SECONDS = 0.0


class SgwCacheEntryModel(BaseModel):
    """Cache entry for serving group worker data."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier for the cache entry.")
    metadata: SgwCacheMetadataModel = Field(default_factory=SgwCacheMetadataModel, description="Cache metadata for the entry.")
    payload: dict[str, JsonScalar] = Field(default_factory=dict, description="JSON-safe placeholder payload for cached SGW data.")


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
    "SgwRefreshErrorModel",
    "SgwRefreshResultModel",
]
