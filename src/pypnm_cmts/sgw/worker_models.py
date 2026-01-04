# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from pypnm_cmts.lib.types import ServiceGroupId


class RefreshLaneType(str, Enum):
    """Refresh lane identifiers for serving group workers."""

    HEAVY = "HEAVY"
    LIGHT = "LIGHT"


class RefreshState(str, Enum):
    """Refresh state for serving group worker lanes and snapshots."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


class RefreshLaneStatusModel(BaseModel):
    """Status payload for a single refresh lane."""

    state: RefreshState = Field(default=RefreshState.IDLE, description="Refresh state for the lane.")
    running: bool = Field(default=False, description="Whether the lane is actively refreshing.")
    last_success_time: datetime | None = Field(default=None, description="UTC timestamp of the last successful refresh.")
    last_error: str = Field(default="", description="Most recent refresh error message, if any.")


class InventoryResultModel(BaseModel):
    """Minimal inventory summary for a serving group."""

    modem_count: int = Field(default=0, description="Number of cable modems in the serving group inventory.")


class StateResultModel(BaseModel):
    """Minimal state summary for a serving group."""

    updated_count: int = Field(default=0, description="Number of modem state records updated in the refresh.")


class ServingGroupSnapshotModel(BaseModel):
    """Cache snapshot for a serving group worker."""

    sg_id: ServiceGroupId = Field(..., description="Service group identifier for this snapshot.")
    snapshot_time: datetime = Field(..., description="UTC timestamp for the snapshot.")
    age_seconds: float = Field(default=0.0, description="Age of the snapshot in seconds.")
    refresh_state: RefreshState = Field(default=RefreshState.IDLE, description="Overall refresh state for the snapshot.")
    heavy_refresh: RefreshLaneStatusModel = Field(default_factory=RefreshLaneStatusModel, description="Heavy refresh lane status.")
    light_refresh: RefreshLaneStatusModel = Field(default_factory=RefreshLaneStatusModel, description="Light refresh lane status.")
    modem_count: int = Field(default=0, description="Cable modem count summary for the snapshot.")


__all__ = [
    "InventoryResultModel",
    "RefreshLaneStatusModel",
    "RefreshLaneType",
    "RefreshState",
    "ServingGroupSnapshotModel",
    "StateResultModel",
]
