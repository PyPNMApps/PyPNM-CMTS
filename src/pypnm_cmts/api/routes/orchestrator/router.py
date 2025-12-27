# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter

from pypnm_cmts.api.routes.orchestrator.schemas import OrchestratorRunRequest
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.orchestrator.models import (
    OrchestratorRunResultModel,
    OrchestratorStatusModel,
)


class OrchestratorRouter:
    """
    FastAPI router for orchestration endpoints.
    """

    def __init__(
        self,
        prefix: str = "/orchestrator",
        tags: list[str | Enum] | None = None,
    ) -> None:
        if tags is None:
            tags = ["Orchestrator"]
        self.router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logging.getLogger(__name__)
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.post(
            "/run",
            response_model=OrchestratorRunResultModel,
            summary="Execute a single orchestration tick",
            description="Executes one orchestration tick using the current coordination backend.",
        )
        def run_once(request: OrchestratorRunRequest) -> OrchestratorRunResultModel:
            """
            **Execute Single Orchestrator Tick**

            This endpoint runs a single coordination tick and returns the structured result payload.
            """
            launcher = CmtsOrchestratorLauncher(
                config_path=request.config_path,
                mode=request.mode,
                sg_id=request.sg_id,
                owner_id=request.owner_id,
                target_service_groups=request.target_service_groups,
                shard_mode=request.shard_mode,
                tick_interval_seconds=request.tick_interval_seconds,
                leader_ttl_seconds=request.leader_ttl_seconds,
                lease_ttl_seconds=request.lease_ttl_seconds,
                state_dir=request.state_dir,
                election_name=request.election_name,
            )
            return launcher.run_once()

        @self.router.post(
            "/status",
            response_model=OrchestratorStatusModel,
            summary="Retrieve orchestration status",
            description="Returns inventory and coordination status without executing a tick.",
        )
        def status(request: OrchestratorRunRequest) -> OrchestratorStatusModel:
            """
            **Retrieve Orchestrator Status**

            This endpoint returns coordination status, leader status, and inventory without running a tick.
            """
            launcher = CmtsOrchestratorLauncher(
                config_path=request.config_path,
                mode=request.mode,
                sg_id=request.sg_id,
                owner_id=request.owner_id,
                target_service_groups=request.target_service_groups,
                shard_mode=request.shard_mode,
                tick_interval_seconds=request.tick_interval_seconds,
                leader_ttl_seconds=request.leader_ttl_seconds,
                lease_ttl_seconds=request.lease_ttl_seconds,
                state_dir=request.state_dir,
                election_name=request.election_name,
            )
            return launcher.build_status_snapshot()


router = OrchestratorRouter().router

__all__ = [
    "router",
]
