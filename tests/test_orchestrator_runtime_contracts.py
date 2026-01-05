# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.coordination.manager import CoordinationManager
from pypnm_cmts.coordination.models import (
    CoordinationStatusModel,
    CoordinationTickResultModel,
)
from pypnm_cmts.lib.types import (
    CoordinationElectionName,
    LeaderId,
    OrchestratorRunId,
    OwnerId,
    ServiceGroupId,
)
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.orchestrator.models import WorkResultModel
from pypnm_cmts.orchestrator.runtime import CmtsOrchestratorRuntime
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


def _write_system_config(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "adapter": {
                "hostname": "cmts.example",
                "community": "public",
            },
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_runtime_controller_tick_with_empty_inventory(tmp_path: Path) -> None:
    state_dir = tmp_path / "coordination"
    settings = CmtsOrchestratorSettings.model_validate(
        {
            "mode": "controller",
            "state_dir": str(state_dir),
            "service_groups": [],
            "adapter": {"hostname": "cmts.example", "community": "public"},
        }
    )
    manager = CoordinationManager(
        state_dir=state_dir,
        election_name=CoordinationElectionName("cmts-primary"),
        leader_id=LeaderId("controller-test"),
        owner_id=OwnerId("controller-test"),
        leader_ttl_seconds=int(settings.leader_ttl_seconds),
        lease_ttl_seconds=int(settings.lease_ttl_seconds),
        target_service_groups=0,
        shard_mode=settings.shard_mode,
        leader_enabled=True,
        leader_id_validator=None,
    )
    runtime = CmtsOrchestratorRuntime(
        settings=settings,
        manager=manager,
        service_groups=[],
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
    )

    results = runtime.run_forever(max_ticks=1, sleeper=lambda _: None)
    assert len(results) == 1
    assert int(results[0].tick_index) == 1


def test_worker_bound_sg_without_lease_returns_empty_work_results(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        return CoordinationTickResultModel(acquired_sg_ids=[])

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.status",
        lambda self: CoordinationStatusModel(held_sg_ids=[]),
    )

    called = {"run_tests": False}

    def _fake_run_tests(
        self: object,
        sg_id: ServiceGroupId,
        tests: list[str],
        run_id: OrchestratorRunId,
    ) -> list[WorkResultModel]:
        called["run_tests"] = True
        return []

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.work_runner.WorkRunner.run_tests",
        _fake_run_tests,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=ServiceGroupId(1),
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.lease_held is False
    assert str(result.run_id) == ""
    assert result.work_results == []
    assert called["run_tests"] is False


def test_run_forever_updates_service_groups_after_leader(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    seen: list[list[int]] = []

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        seen.append([int(sg_id) for sg_id in service_groups])
        return CoordinationTickResultModel(acquired_sg_ids=[])

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )

    statuses = iter([False, True, True, True])

    def _fake_status(self: object) -> CoordinationStatusModel:
        try:
            is_leader = next(statuses)
        except StopIteration:
            is_leader = True
        return CoordinationStatusModel(
            is_leader=is_leader,
            held_sg_ids=[],
        )

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.status",
        _fake_status,
    )

    def _fake_build_controller_service_groups(
        self: object,
        settings: CmtsOrchestratorSettings,
        state_dir: Path,
        is_leader: bool,
    ) -> tuple[list[ServiceGroupId], str]:
        if is_leader:
            return ([ServiceGroupId(2)], "config")
        return ([ServiceGroupId(1)], "config")

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher._build_controller_service_groups",
        _fake_build_controller_service_groups,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.COMBINED,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    launcher.run_forever(max_ticks=3, sleeper=lambda _: None)

    assert len(seen) == 3
    assert seen[0] == [1]
    assert seen[1] == [1]
    assert seen[2] == [2]
