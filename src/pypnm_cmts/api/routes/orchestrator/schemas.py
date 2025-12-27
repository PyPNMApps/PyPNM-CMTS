# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    CoordinationPath,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


class OrchestratorRunRequest(BaseModel):
    """Request payload for orchestrator execution endpoints."""

    mode: OrchestratorMode = Field(..., description="Execution mode: standalone, controller, or worker.")
    config_path: CoordinationPath | None = Field(default=None, description="Optional path to system.json configuration file.")
    sg_id: ServiceGroupId | None = Field(default=None, description="Service group id (required for worker mode).")
    owner_id: OwnerId | None = Field(default=None, description="Optional owner id override for coordination.")
    target_service_groups: int | None = Field(default=None, description="Optional target service groups override.")
    shard_mode: str | None = Field(default=None, description="Optional shard mode override.")
    tick_interval_seconds: float | None = Field(default=None, description="Optional tick interval override (seconds).")
    leader_ttl_seconds: int | None = Field(default=None, description="Optional leader TTL override (seconds).")
    lease_ttl_seconds: int | None = Field(default=None, description="Optional lease TTL override (seconds).")
    state_dir: CoordinationPath | None = Field(default=None, description="Optional coordination state directory override.")
    election_name: CoordinationElectionName | None = Field(default=None, description="Optional election name override.")

    @model_validator(mode="after")
    def _validate_worker_sg(self) -> OrchestratorRunRequest:
        if self.mode == OrchestratorMode.WORKER and self.sg_id is None:
            raise ValueError("sg_id is required when mode=worker.")
        return self


__all__ = [
    "OrchestratorRunRequest",
]
