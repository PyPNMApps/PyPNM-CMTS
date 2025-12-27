# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
import time
from pathlib import Path

from pypnm_cmts.lib.types import (
    OrchestratorRunId,
    ServiceGroupId,
)
from pypnm_cmts.orchestrator.models import (
    WorkItemModel,
    WorkResultModel,
    WorkStatus,
)

RESULTS_DIR_NAME = "results"
MIN_DURATION_SECONDS = 0.000001
TEST_NAME_SEPARATOR = "_"


class WorkRunner:
    """
    Placeholder work runner for Phase-3 deterministic test execution.
    """

    def __init__(self, state_dir: Path) -> None:
        """
        Initialize the work runner.

        Args:
            state_dir (Path): Base coordination state directory for result persistence.
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._state_dir = state_dir

    def run_tests(self, sg_id: ServiceGroupId, tests: list[str], run_id: OrchestratorRunId) -> list[WorkResultModel]:
        """
        Execute placeholder tests for a service group and persist results.

        Args:
            sg_id (ServiceGroupId): Service group identifier to run tests for.
            tests (list[str]): List of test names to execute.
            run_id (OrchestratorRunId): Deterministic run identifier for persistence naming.

        Returns:
            list[WorkResultModel]: Work results for each requested test.
        """
        results: list[WorkResultModel] = []
        if not tests:
            return results

        for test_name in tests:
            item = WorkItemModel(
                sg_id=sg_id,
                test_name=str(test_name),
                run_id=run_id,
            )
            start_time = time.perf_counter()
            end_time = time.perf_counter()
            duration = max(end_time - start_time, MIN_DURATION_SECONDS)

            result = WorkResultModel(
                sg_id=sg_id,
                test_name=item.test_name,
                status=WorkStatus.SUCCESS,
                duration_seconds=duration,
                error_message="",
            )
            results.append(result)
            self._persist_result(item, result)

        return results

    def _persist_result(self, item: WorkItemModel, result: WorkResultModel) -> None:
        try:
            path = self._result_path(item)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = result.model_dump_json(indent=2)
            path.write_text(payload, encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"Failed to persist work result for {item.test_name}: {exc}")

    def _result_path(self, item: WorkItemModel) -> Path:
        test_name = self._sanitize_test_name(item.test_name)
        filename = f"{item.run_id}_{test_name}.json"
        return self._state_dir / RESULTS_DIR_NAME / f"sg_{int(item.sg_id)}" / filename

    def _sanitize_test_name(self, value: str) -> str:
        name = value.strip()
        name = name.replace("/", TEST_NAME_SEPARATOR)
        name = name.replace("\\", TEST_NAME_SEPARATOR)
        return name


__all__ = [
    "WorkRunner",
]
