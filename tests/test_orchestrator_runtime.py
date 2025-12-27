# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    LeaderId,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.orchestrator.runtime import CmtsOrchestratorRuntime
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


def _build_settings(tmp_path: Path) -> CmtsOrchestratorSettings:
    return CmtsOrchestratorSettings(
        tick_interval_seconds=1,
        leader_ttl_seconds=5,
        lease_ttl_seconds=5,
        state_dir=tmp_path / "coordination",
    )


def test_runtime_runs_fixed_ticks_without_sleep(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
    )

    service_groups = [ServiceGroupId(1)]
    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=service_groups,
        mode=OrchestratorMode.STANDALONE,
    )

    results = runtime.run_forever(max_ticks=3, sleeper=lambda _: None)
    assert len(results) == 3


def test_runtime_stop_prevents_ticks(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    manager = CoordinationManager(
        state_dir=settings.state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        leader_id=LeaderId("leader-1"),
        owner_id=OwnerId("owner-1"),
        leader_ttl_seconds=settings.leader_ttl_seconds,
        lease_ttl_seconds=settings.lease_ttl_seconds,
        target_service_groups=1,
        shard_mode="sequential",
    )

    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[ServiceGroupId(1)],
        mode=OrchestratorMode.STANDALONE,
    )

    runtime.stop()
    results = runtime.run_forever(max_ticks=2, sleeper=lambda _: None)
    assert results == []
