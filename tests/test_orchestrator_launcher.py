# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypnm.lib.types import HostNameStr

from pypnm_cmts.cmts.discovery_models import InventoryDiscoveryResultModel
from pypnm_cmts.coordination.models import (
    CoordinationStatusModel,
    CoordinationTickResultModel,
)
from pypnm_cmts.lib.types import OrchestratorRunId, OwnerId, ServiceGroupId, TickIndex
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.orchestrator.models import OrchestratorRunResultModel, WorkResultModel
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


def _write_system_config(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
                {"sg_id": 2, "name": "sg-2", "enabled": False},
                {"sg_id": 3, "name": "sg-3", "enabled": True},
            ],
            "target_service_groups": 2,
            "shard_mode": "sequential",
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_system_config_only_disabled(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": False},
            ],
            "target_service_groups": 2,
            "shard_mode": "sequential",
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_system_config_multi(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "service_groups": [
                {"sg_id": 1, "name": "sg-1", "enabled": True},
                {"sg_id": 2, "name": "sg-2", "enabled": True},
            ],
            "target_service_groups": 1,
            "shard_mode": "sequential",
            "default_tests": ["test-a"],
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_system_config_auto_discover(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "auto_discover": True,
            "adapter": {
                "hostname": "192.168.0.100",
                "community": "public",
                "port": 161,
            },
            "service_groups": [],
            "target_service_groups": 2,
            "shard_mode": "sequential",
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_launcher_standalone_inventory(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.mode == OrchestratorMode.STANDALONE
    assert result.inventory.count == 2
    assert [int(sg_id) for sg_id in result.inventory.sg_ids] == [1, 3]
    assert result.target_service_groups == 2


def test_launcher_controller_inventory(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.mode == OrchestratorMode.CONTROLLER
    assert result.inventory.count == 2
    assert [int(sg_id) for sg_id in result.inventory.sg_ids] == [1, 3]
    assert result.target_service_groups == 2


def test_launcher_worker_inventory_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=ServiceGroupId(1),
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.mode == OrchestratorMode.WORKER
    assert result.inventory.count == 1
    assert [int(sg_id) for sg_id in result.inventory.sg_ids] == [1]
    assert result.target_service_groups == 1


def test_launcher_parse_sg_id_rejects_non_numeric() -> None:
    with pytest.raises(ValueError, match="service group id must be a numeric value"):
        CmtsOrchestratorLauncher._parse_sg_id("sg-1")


def test_launcher_worker_rejects_sg_id_not_enabled(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config_only_disabled(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=ServiceGroupId(1),
        state_dir_override=tmp_path / "coordination",
    )

    with pytest.raises(ValueError, match="worker sg-id is not enabled in configuration"):
        launcher.run_once()


def test_launcher_worker_allows_unbound_mode(tmp_path: Path, monkeypatch: object) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        return CoordinationTickResultModel(acquired_sg_ids=[])

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.mode == OrchestratorMode.WORKER
    assert [int(sg_id) for sg_id in result.inventory.sg_ids] == [1, 3]


def test_model_a_controller_and_workers_share_inventory_snapshot(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config_multi(config_path)

    controller = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=state_dir,
    )
    controller_result = controller.run_once()
    assert controller_result.lease_held is False
    snapshot_path = state_dir / "inventory" / "discovery.json"
    assert snapshot_path.exists()

    worker_results: list[OrchestratorRunResultModel] = []

    def _collect_worker(result: OrchestratorRunResultModel) -> None:
        worker_results.append(result)

    worker_1 = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=None,
        owner_id=OwnerId("worker-1"),
        state_dir_override=state_dir,
    )
    worker_1.run_forever(on_tick=_collect_worker, max_ticks=2, sleeper=lambda _: None)

    worker_2 = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=None,
        owner_id=OwnerId("worker-2"),
        state_dir_override=state_dir,
    )
    worker_2.run_forever(on_tick=_collect_worker, max_ticks=2, sleeper=lambda _: None)

    assert worker_results


def test_worker_does_not_write_leader_record(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=ServiceGroupId(1),
        state_dir_override=state_dir,
    )

    launcher.run_once()

    leader_record = state_dir / "cmts-primary.json"
    assert leader_record.exists() is False


def test_controller_overwrites_worker_leader_record(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    leader_record = {
        "election_name": "cmts-primary",
        "leader_id": "worker-1",
        "acquired_at": 1.0,
        "expires_at": 9999.0,
    }
    leader_path = state_dir / "cmts-primary.json"
    leader_path.parent.mkdir(parents=True, exist_ok=True)
    leader_path.write_text(json.dumps(leader_record), encoding="utf-8")

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=state_dir,
    )

    result = launcher.run_once()
    assert result.leader_status.is_leader is True
    assert str(result.leader_status.leader_id).startswith("worker-") is False

    persisted = json.loads(leader_path.read_text(encoding="utf-8"))
    assert str(persisted.get("leader_id", "")).startswith("worker-") is False


def test_controller_overwrites_empty_leader_record(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    leader_record = {
        "election_name": "cmts-primary",
        "leader_id": "",
        "acquired_at": 1.0,
        "expires_at": 9999.0,
    }
    leader_path = state_dir / "cmts-primary.json"
    leader_path.parent.mkdir(parents=True, exist_ok=True)
    leader_path.write_text(json.dumps(leader_record), encoding="utf-8")

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=state_dir,
    )

    result = launcher.run_once()
    assert result.leader_status.is_leader is True
    assert str(result.leader_status.leader_id).strip() != ""
    assert str(result.leader_status.leader_id).startswith("worker-") is False

    persisted = json.loads(leader_path.read_text(encoding="utf-8"))
    persisted_id = str(persisted.get("leader_id", "")).strip()
    assert persisted_id != ""
    assert persisted_id.startswith("worker-") is False


def test_controller_restart_retains_leader_identity(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    first = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=state_dir,
    )
    first_result = first.run_once()
    first_leader_id = str(first_result.leader_status.leader_id)
    assert first_leader_id != ""

    second = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=state_dir,
    )
    second_result = second.run_once()
    assert second_result.leader_status.is_leader is True
    assert str(second_result.leader_status.leader_id) == first_leader_id


def test_controller_rewrites_worker_prefixed_owner_id(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        owner_id=OwnerId("worker-foo"),
        state_dir_override=state_dir,
    )

    result = launcher.run_once()
    leader_id = str(result.leader_status.leader_id)
    assert leader_id.startswith("controller-")
    assert leader_id.startswith("worker-") is False


def test_worker_rewrites_controller_prefixed_owner_id(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=ServiceGroupId(1),
        owner_id=OwnerId("controller-foo"),
        state_dir_override=tmp_path / "coordination",
    )

    leader_id = launcher._build_leader_id(OwnerId("controller-foo"))
    assert str(leader_id).startswith("worker-")
    assert str(leader_id).startswith("controller-") is False


def test_launcher_no_enabled_service_groups_returns_empty_inventory(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config_only_disabled(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.inventory.count == 0
    assert result.target_service_groups == 0
    assert result.coordination_tick.acquired_sg_ids == []


def test_launcher_run_once_uses_tick_index_from_coordination(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        return CoordinationTickResultModel(tick_index=TickIndex(7))

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert int(result.tick_index) == 7


def test_build_status_snapshot_does_not_tick(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _tick_should_not_run(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        raise AssertionError("tick should not be called during build_status_snapshot")

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _tick_should_not_run,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.build_status_snapshot()
    assert result.inventory.count == 2


def test_launcher_uses_discovery_when_auto_discover_enabled(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config_auto_discover(config_path)

    async def _fake_discover(self: object, state_dir: Path | None = None) -> InventoryDiscoveryResultModel:
        return InventoryDiscoveryResultModel(
            cmts_host=HostNameStr("192.168.0.100"),
            discovered_sg_ids=[ServiceGroupId(2), ServiceGroupId(1)],
            per_sg=[],
        )

    monkeypatch.setattr(
        "pypnm_cmts.cmts.inventory_discovery.CmtsInventoryDiscoveryService.discover_inventory",
        _fake_discover,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.STANDALONE,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.inventory.source == "discovery"
    assert [int(sg_id) for sg_id in result.inventory.sg_ids] == [1, 2]


def test_worker_run_once_without_lease_does_not_persist_results(
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

    state_dir = tmp_path / "coordination"
    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=ServiceGroupId(1),
        state_dir_override=state_dir,
    )

    result = launcher.run_once()
    assert result.lease_held is False
    assert str(result.run_id) == ""
    assert result.work_results == []


def test_unbound_worker_without_lease_returns_empty_work_results(
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

    state_dir = tmp_path / "coordination"
    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=None,
        state_dir_override=state_dir,
    )

    result = launcher.run_once()
    assert result.lease_held is False
    assert str(result.run_id) == ""
    assert result.work_results == []


def test_combined_run_once_behaves_like_controller_and_worker(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        return CoordinationTickResultModel(acquired_sg_ids=[ServiceGroupId(1)])

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.status",
        lambda self: CoordinationStatusModel(held_sg_ids=[ServiceGroupId(1)]),
    )

    captured: dict[str, ServiceGroupId] = {}

    def _fake_run_tests(
        self: object,
        sg_id: ServiceGroupId,
        tests: list[str],
        run_id: OrchestratorRunId,
    ) -> list[WorkResultModel]:
        captured["sg_id"] = sg_id
        return []

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.work_runner.WorkRunner.run_tests",
        _fake_run_tests,
    )

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.COMBINED,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    result = launcher.run_once()
    assert result.mode == OrchestratorMode.COMBINED
    assert result.lease_held is True
    assert str(result.run_id).startswith("sg1_tick")
    assert int(captured["sg_id"]) == 1


def test_combined_run_forever_surfaces_held_leases_and_runs_work(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        return CoordinationTickResultModel(acquired_sg_ids=[ServiceGroupId(1)])

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.status",
        lambda self: CoordinationStatusModel(held_sg_ids=[ServiceGroupId(1)]),
    )

    captured: dict[str, ServiceGroupId] = {}

    def _fake_run_tests(
        self: object,
        sg_id: ServiceGroupId,
        tests: list[str],
        run_id: OrchestratorRunId,
    ) -> list[WorkResultModel]:
        captured["sg_id"] = sg_id
        return []

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.work_runner.WorkRunner.run_tests",
        _fake_run_tests,
    )

    results: list[OrchestratorRunResultModel] = []

    def _collect(result: OrchestratorRunResultModel) -> None:
        results.append(result)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.COMBINED,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    launcher.run_forever(on_tick=_collect, max_ticks=1, sleeper=lambda _: None)

    assert results
    assert results[0].lease_held is True
    assert int(captured["sg_id"]) == 1
    assert [int(sg_id) for sg_id in results[0].coordination_tick.leased_sg_ids] == [1]


def test_worker_runs_single_sg_when_multiple_acquired(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _fake_tick(self: object, service_groups: list[ServiceGroupId]) -> CoordinationTickResultModel:
        return CoordinationTickResultModel(acquired_sg_ids=[ServiceGroupId(3), ServiceGroupId(1)])

    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.tick",
        _fake_tick,
    )
    monkeypatch.setattr(
        "pypnm_cmts.coordination.manager.CoordinationManager.status",
        lambda self: CoordinationStatusModel(held_sg_ids=[ServiceGroupId(1)]),
    )

    captured: dict[str, ServiceGroupId] = {}

    def _fake_run_tests(
        self: object,
        sg_id: ServiceGroupId,
        tests: list[str],
        run_id: OrchestratorRunId,
    ) -> list[WorkResultModel]:
        captured["sg_id"] = sg_id
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
    assert int(captured["sg_id"]) == 1
    assert str(result.run_id).startswith("sg1_tick")
