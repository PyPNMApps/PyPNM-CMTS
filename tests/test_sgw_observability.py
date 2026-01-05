# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import logging

import pytest

from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.manager import (
    REFRESH_MODE_HEAVY,
    REFRESH_MODE_LIGHT,
    REFRESH_MODE_NONE,
    REFRESH_RESULT_ERROR,
    REFRESH_RESULT_OK,
    REFRESH_RESULT_STALE,
    SgwManager,
)
from pypnm_cmts.sgw.metrics import InMemorySgwMetrics
from pypnm_cmts.sgw.models import (
    SgwCacheEntryModel,
    SgwSnapshotModel,
    SgwSnapshotPayloadModel,
)
from pypnm_cmts.sgw.store import SgwCacheStore


@pytest.mark.unit
def test_sgw_manager_logs_refresh_fields(caplog: pytest.LogCaptureFixture) -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    sg_id = ServiceGroupId(21)
    store = SgwCacheStore()
    metrics = InMemorySgwMetrics()
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: SgwSnapshotPayloadModel(),
        metrics=metrics,
    )

    caplog.set_level(logging.INFO)
    manager.refresh_once(1_000.0)

    records = [record for record in caplog.records if record.name == "SgwManager"]
    assert records
    record = records[0]
    assert record.sg_id == int(sg_id)
    assert record.refresh_mode in (REFRESH_MODE_HEAVY, REFRESH_MODE_LIGHT, REFRESH_MODE_NONE)
    assert record.duration_ms >= 0.0
    assert record.result in (REFRESH_RESULT_OK, REFRESH_RESULT_ERROR, REFRESH_RESULT_STALE)
    assert record.snapshot_time_epoch >= 0.0
    assert record.age_seconds >= 0.0
    assert record.interval_seconds >= 0.0
    if record.refresh_mode == REFRESH_MODE_HEAVY:
        assert record.interval_seconds == float(settings.sgw.poll_heavy_seconds)
    elif record.refresh_mode == REFRESH_MODE_LIGHT:
        assert record.interval_seconds == float(settings.sgw.poll_light_seconds)
    else:
        assert record.interval_seconds == 0.0


@pytest.mark.unit
def test_sgw_manager_metrics_capture_refresh_and_stale() -> None:
    settings = CmtsOrchestratorSettings.model_validate(
        {
            "adapter": {"hostname": "cmts.example", "community": "public"},
            "sgw": {
                "cache_max_age_seconds": 1,
                "poll_light_seconds": 1,
                "poll_heavy_seconds": 1,
                "refresh_jitter_seconds": 0,
            }
        }
    )
    sg_id = ServiceGroupId(22)
    store = SgwCacheStore()
    metrics = InMemorySgwMetrics()
    manager = SgwManager(
        settings=settings,
        store=store,
        service_groups=[sg_id],
        jitter_provider=lambda *_args: 0,
        heavy_poller=lambda *_args: SgwSnapshotPayloadModel(),
        metrics=metrics,
    )

    manager.refresh_once(1_000.0)

    now_epoch = 1_005.0
    metadata = SgwCacheMetadataModel(
        snapshot_time_epoch=1.0,
        last_heavy_refresh_epoch=now_epoch,
        last_light_refresh_epoch=now_epoch,
    )
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))

    manager.refresh_once(now_epoch)

    assert metrics.refresh_durations_ms.get(REFRESH_MODE_HEAVY)
    assert metrics.staleness_count >= 1
