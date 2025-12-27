# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pypnm_cmts.coordination.models import CoordinationTickResultModel
from pypnm_cmts.lib.types import ServiceGroupId, TickIndex
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
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


def test_launcher_worker_requires_sg_id(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.WORKER,
        sg_id=None,
        state_dir_override=tmp_path / "coordination",
    )

    with pytest.raises(ValueError, match="worker mode requires --sg-id"):
        launcher.run_once()


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


def test_worker_run_once_without_lease_does_not_persist_results(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "system.json"
    _write_system_config(config_path)

    def _lease_not_held(
        self: CmtsOrchestratorLauncher,
        manager: object,
        service_groups: list[ServiceGroupId],
    ) -> bool:
        return False

    monkeypatch.setattr(
        "pypnm_cmts.orchestrator.launcher.CmtsOrchestratorLauncher._is_worker_lease_held",
        _lease_not_held,
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

    results_root = state_dir / "results"
    if results_root.exists():
        assert list(results_root.glob("sg_*")) == []
        assert list(results_root.rglob("*.json")) == []
