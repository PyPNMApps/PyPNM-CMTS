# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.sgw.manager import REFRESH_MODE_HEAVY, SgwManager
from pypnm_cmts.sgw.metrics import InMemorySgwMetrics
from pypnm_cmts.sgw.models import SgwSnapshotPayloadModel
from pypnm_cmts.sgw.store import SgwCacheStore


@pytest.mark.unit
def test_sgw_manager_records_duration_on_error() -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {
            "adapter": {"hostname": "cmts.example", "community": "public"},
            "sgw": {
                "poll_light_seconds": 1,
                "poll_heavy_seconds": 1,
                "refresh_jitter_seconds": 0,
            }
        }
    )
    sg_id = ServiceGroupId(9)
    store = SgwCacheStore()
    metrics = InMemorySgwMetrics()

    def _raise(
        _sg_id: ServiceGroupId,
        _settings: CmtsOrchestratorSettings,
    ) -> SgwSnapshotPayloadModel:
        raise RuntimeError("  bad error  ")

    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=_raise,
        metrics=metrics,
    )

    manager.refresh_once(1_000.0)

    assert metrics.refresh_durations_ms.get(REFRESH_MODE_HEAVY)
    assert metrics.refresh_error_counts.get(REFRESH_MODE_HEAVY) == 1
    entry = store.get_entry(sg_id)
    assert entry is not None
    assert entry.snapshot.metadata.last_error == "bad error"
