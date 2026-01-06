# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import json
from pathlib import Path

from pypnm_cmts.coordination.service_group_lease import FileServiceGroupLease
from pypnm_cmts.lib.types import CoordinationElectionName, OwnerId, ServiceGroupId
from pypnm_cmts.orchestrator.launcher import CmtsOrchestratorLauncher
from pypnm_cmts.types.orchestrator_types import OrchestratorMode


def _write_controller_config(path: Path) -> None:
    payload = {
        "CmtsOrchestrator": {
            "service_groups": [
                {"sg_id": 1, "enabled": True},
                {"sg_id": 2, "enabled": True},
                {"sg_id": 3, "enabled": True},
            ],
            "target_service_groups": 2,
            "shard_mode": "sequential",
            "worker_cap": 0,
            "election_name": "cmts-test",
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_controller_tick_reports_desired_and_conflicts(tmp_path: Path) -> None:
    config_path = tmp_path / "system.json"
    state_dir = tmp_path / "coordination"
    _write_controller_config(config_path)

    lease = FileServiceGroupLease(
        state_dir=state_dir,
        election_name=CoordinationElectionName("cmts-test"),
        sg_id=ServiceGroupId(2),
        owner_id=OwnerId("other"),
        ttl_seconds=30,
    )
    lease.try_acquire()

    launcher = CmtsOrchestratorLauncher(
        config_path=config_path,
        mode=OrchestratorMode.CONTROLLER,
        sg_id=None,
        state_dir_override=state_dir,
    )

    result = launcher.run_once()
    tick = result.coordination_tick

    assert [int(sg_id) for sg_id in tick.enabled_sg_ids] == [1, 2, 3]
    assert [int(sg_id) for sg_id in tick.desired_sg_ids] == [1, 2, 3]
    assert int(tick.worker_count) == 2

    leased = [int(sg_id) for sg_id in tick.leased_sg_ids]
    assert leased == []

    conflicts = [conflict for conflict in tick.conflicts if int(conflict.sg_id) == 2]
    assert conflicts
    assert str(conflicts[0].owner_id) == "other"
    assert conflicts[0].reason != ""
