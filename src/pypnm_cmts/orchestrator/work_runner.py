# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import logging
import time
from pathlib import Path

from pypnm_cmts.lib.types import (
    OrchestratorRunId,
    PnmTestName,
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

    def run_pnm_tests(
        self,
        sg_id: ServiceGroupId,
        pnm_tests: list[PnmTestName],
        run_id: OrchestratorRunId,
    ) -> list[WorkResultModel]:
        """
        Execute placeholder tests for a service group and persist results.

        Args:
            sg_id (ServiceGroupId): Service group identifier to run tests for.
            pnm_tests (list[PnmTestName]): Ordered orchestrator PNM operation keys to execute for the service group,
                typically sourced from orchestrator default_tests (for example ds_ofdm_rxmer).
            run_id (OrchestratorRunId): Deterministic run identifier for persistence naming.

        Returns:
            list[WorkResultModel]: Work results for each requested PNM operation key.
        """
        results: list[WorkResultModel] = []
        if not pnm_tests:
            return results

        for pnm_test_name in pnm_tests:
            item = WorkItemModel(
                sg_id=sg_id,
                test_name=str(pnm_test_name),
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
            pnm_test_name = item.test_name
            path = self._result_path(item)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = result.model_dump_json(indent=2)
            path.write_text(payload, encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"Failed to persist work result for {pnm_test_name}: {exc}")

    def _result_path(self, item: WorkItemModel) -> Path:
        pnm_test_name = self._sanitize_test_name(item.test_name)
        filename = f"{item.run_id}_{pnm_test_name}.json"
        return self._state_dir / RESULTS_DIR_NAME / f"sg_{int(item.sg_id)}" / filename

    def _sanitize_test_name(self, value: str) -> str:
        pnm_name = value.strip()
        pnm_name = pnm_name.replace("/", TEST_NAME_SEPARATOR)
        pnm_name = pnm_name.replace("\\", TEST_NAME_SEPARATOR)
        return pnm_name


__all__ = [
    "WorkRunner",
]
