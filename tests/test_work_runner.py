# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

from pathlib import Path

from pypnm_cmts.lib.types import (
    OrchestratorRunId,
    ServiceGroupId,
)
from pypnm_cmts.orchestrator.models import WorkStatus
from pypnm_cmts.orchestrator.work_runner import WorkRunner


def test_work_runner_returns_results_and_persists(tmp_path: Path) -> None:
    state_dir = tmp_path / "coordination"
    runner = WorkRunner(state_dir=state_dir)

    run_id = OrchestratorRunId("sg7_tick000001")
    results = runner.run_tests(ServiceGroupId(7), ["test-a", "test-b"], run_id=run_id)
    assert len(results) == 2
    for result in results:
        assert result.status == WorkStatus.SUCCESS
        assert result.duration_seconds > 0
        assert result.error_message == ""

    result_dir = state_dir / "results" / "sg_7"
    assert result_dir.exists()
    persisted = list(result_dir.glob("*.json"))
    assert len(persisted) == 2
    for path in persisted:
        assert path.name.startswith(str(run_id))
