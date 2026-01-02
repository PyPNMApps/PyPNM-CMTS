# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from pypnm_cmts.coordination.models import (
    CoordinationStatusModel,
    CoordinationTickResultModel,
    LeaderElectionStatusModel,
)
from pypnm_cmts.lib.types import (
    OrchestratorRunId,
    ServiceGroupId,
    TickIndex,
)
from pypnm_cmts.types.orchestrator_types import OrchestratorMode

SGW_LAST_ERROR_MAX_LENGTH = 256


class ServiceGroupInventoryModel(BaseModel):
    """Inventory of service groups supplied to orchestration."""

    sg_ids: list[ServiceGroupId] = Field(default_factory=list, description="Service group identifiers included in the inventory.")
    count: int = Field(default=0, description="Total number of service groups in the inventory.")
    source: str = Field(default="", description="Inventory source label (config or worker input).")


class WorkStatus(str, Enum):
    """Status values for work execution results."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkItemModel(BaseModel):
    """Work item describing a service-group test execution."""

    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the work item.")
    test_name: str = Field(default="", description="Test name to execute for the service group.")
    run_id: OrchestratorRunId = Field(default=OrchestratorRunId(""), description="Run identifier associated with the work item.")


class WorkResultModel(BaseModel):
    """Result payload for a single test execution."""

    sg_id: ServiceGroupId = Field(default=ServiceGroupId(0), description="Service group identifier associated with the result.")
    test_name: str = Field(default="", description="Test name executed for the service group.")
    status: WorkStatus = Field(default=WorkStatus.SUCCESS, description="Execution status for the work item.")
    duration_seconds: float = Field(default=0.0, description="Execution duration in seconds.")
    error_message: str = Field(default="", description="Optional error message for failed work.")


class SgwRefreshState(str, Enum):
    """Refresh state values for SGW cache metadata."""

    OK = "OK"
    STALE = "STALE"
    ERROR = "ERROR"


class SgwCacheMetadataModel(BaseModel):
    """Snapshot metadata for serving group worker caches."""

    snapshot_time_epoch: float = Field(default=0.0, ge=0.0, description="Snapshot timestamp in epoch seconds.")
    age_seconds: float = Field(default=0.0, ge=0.0, description="Age of the snapshot in seconds.")
    last_heavy_refresh_epoch: float | None = Field(default=None, ge=0.0, description="Epoch timestamp for the last heavy refresh.")
    last_light_refresh_epoch: float | None = Field(default=None, ge=0.0, description="Epoch timestamp for the last light refresh.")
    refresh_state: SgwRefreshState = Field(default=SgwRefreshState.OK, description="Refresh state for the cache entry.")
    last_error: str | None = Field(default=None, max_length=SGW_LAST_ERROR_MAX_LENGTH, description="Optional bounded error message.")


class OrchestratorRunResultModel(BaseModel):
    """Result payload for a single orchestrator tick."""

    mode: OrchestratorMode = Field(default=OrchestratorMode.STANDALONE, description="Execution mode for the orchestrator.")
    tick_index: TickIndex = Field(default=TickIndex(0), description="0 means unset; emitted ticks are 1-based within the current run.")
    run_id: OrchestratorRunId = Field(default=OrchestratorRunId(""), description="Deterministic run identifier used for persistence naming.")
    lease_held: bool = Field(default=False, description="Whether the worker holds the lease for its service group on this tick.")
    inventory: ServiceGroupInventoryModel = Field(default_factory=ServiceGroupInventoryModel, description="Service group inventory for the tick.")
    coordination_tick: CoordinationTickResultModel = Field(default_factory=CoordinationTickResultModel, description="Coordination manager tick result.")
    coordination_status: CoordinationStatusModel = Field(default_factory=CoordinationStatusModel, description="Coordination manager status snapshot.")
    leader_status: LeaderElectionStatusModel = Field(default_factory=LeaderElectionStatusModel, description="Leader election status snapshot.")
    target_service_groups: int = Field(default=0, description="Effective target service group count for this tick.")
    work_results: list[WorkResultModel] = Field(default_factory=list, description="Work execution results produced by this tick.")


class OrchestratorStatusModel(BaseModel):
    """Status snapshot payload for orchestration without executing a tick."""

    mode: OrchestratorMode = Field(default=OrchestratorMode.STANDALONE, description="Execution mode for the orchestrator.")
    inventory: ServiceGroupInventoryModel = Field(default_factory=ServiceGroupInventoryModel, description="Service group inventory for the run.")
    coordination_status: CoordinationStatusModel = Field(default_factory=CoordinationStatusModel, description="Coordination manager status snapshot.")
    leader_status: LeaderElectionStatusModel = Field(default_factory=LeaderElectionStatusModel, description="Leader election status snapshot.")
    target_service_groups: int = Field(default=0, description="Effective target service group count for this run.")


__all__ = [
    "OrchestratorRunResultModel",
    "OrchestratorStatusModel",
    "SgwCacheMetadataModel",
    "SgwRefreshState",
    "SGW_LAST_ERROR_MAX_LENGTH",
    "ServiceGroupInventoryModel",
    "WorkItemModel",
    "WorkResultModel",
    "WorkStatus",
]
