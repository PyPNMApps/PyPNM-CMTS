# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.api.routes.serving_group.schemas import (
    GetServingGroupCableModemsRequest,
)
from pypnm_cmts.api.routes.serving_group.service import ServingGroupCacheService
from pypnm_cmts.config.orchestrator_config import CmtsOrchestratorSettings
from pypnm_cmts.lib.types import ServiceGroupId
from pypnm_cmts.orchestrator.models import SgwCacheMetadataModel
from pypnm_cmts.sgw.manager import SgwManager
from pypnm_cmts.sgw.models import SgwCacheEntryModel, SgwSnapshotModel
from pypnm_cmts.sgw.runtime_state import (
    reset_sgw_runtime_state,
    set_sgw_startup_success,
)
from pypnm_cmts.sgw.store import SgwCacheStore


def _seed_snapshot(store: SgwCacheStore, sg_id: ServiceGroupId, snapshot_time: float) -> None:
    metadata = SgwCacheMetadataModel(snapshot_time_epoch=snapshot_time, age_seconds=0.0)
    snapshot = SgwSnapshotModel(sg_id=sg_id, metadata=metadata)
    store.upsert_entry(SgwCacheEntryModel(sg_id=sg_id, snapshot=snapshot))


@pytest.mark.unit
def test_aggregate_require_fresh_waits_for_all(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    service = ServingGroupCacheService()
    store = SgwCacheStore()
    sg_ids = [ServiceGroupId(1), ServiceGroupId(2)]
    for sg_id in sg_ids:
        _seed_snapshot(store, sg_id, 1_000.0)

    settings = CmtsOrchestratorSettings()
    manager = SgwManager(settings=settings, store=store, service_groups=sg_ids)
    set_sgw_startup_success(sg_ids, store, manager, 1_000.0)

    call_state = {"count": 0}

    def _fake_sleep(_: float) -> None:
        call_state["count"] += 1
        if call_state["count"] == 1:
            entry = store.get_entry(sg_ids[0])
            if entry is not None:
                metadata = entry.snapshot.metadata.model_copy(update={"snapshot_time_epoch": 2_000.0})
                entry.snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
                store.upsert_entry(entry)
        elif call_state["count"] == 2:
            entry = store.get_entry(sg_ids[1])
            if entry is not None:
                metadata = entry.snapshot.metadata.model_copy(update={"snapshot_time_epoch": 2_000.0})
                entry.snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
                store.upsert_entry(entry)

    monotonic_state = {"value": 0.0}

    def _fake_monotonic() -> float:
        monotonic_state["value"] += 0.1
        return monotonic_state["value"]

    monkeypatch.setattr(ServingGroupCacheService, "_sleep", staticmethod(_fake_sleep))
    monkeypatch.setattr(ServingGroupCacheService, "_monotonic", staticmethod(_fake_monotonic))

    request = GetServingGroupCableModemsRequest(
        sg_id=ServiceGroupId(0),
        page=1,
        page_size=1,
        require_fresh=True,
        max_wait_seconds=5.0,
    )

    waited_seconds = service._wait_for_refresh(
        request=request,
        sg_ids=sg_ids,
        store=store,
        refresh_applied=True,
    )

    assert waited_seconds > 0.0
    assert call_state["count"] >= 2


@pytest.mark.unit
def test_aggregate_require_fresh_times_out_when_not_all_advance(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    service = ServingGroupCacheService()
    store = SgwCacheStore()
    sg_ids = [ServiceGroupId(1), ServiceGroupId(2)]
    for sg_id in sg_ids:
        _seed_snapshot(store, sg_id, 1_000.0)

    settings = CmtsOrchestratorSettings()
    manager = SgwManager(settings=settings, store=store, service_groups=sg_ids)
    set_sgw_startup_success(sg_ids, store, manager, 1_000.0)

    sleep_calls = {"count": 0}

    def _fake_sleep(_: float) -> None:
        sleep_calls["count"] += 1
        entry = store.get_entry(sg_ids[0])
        if entry is not None:
            metadata = entry.snapshot.metadata.model_copy(update={"snapshot_time_epoch": 2_000.0})
            entry.snapshot = entry.snapshot.model_copy(update={"metadata": metadata})
            store.upsert_entry(entry)

    monotonic_state = {"value": 0.0}

    def _fake_monotonic() -> float:
        monotonic_state["value"] += 0.3
        return monotonic_state["value"]

    monkeypatch.setattr(ServingGroupCacheService, "_sleep", staticmethod(_fake_sleep))
    monkeypatch.setattr(ServingGroupCacheService, "_monotonic", staticmethod(_fake_monotonic))

    request = GetServingGroupCableModemsRequest(
        sg_id=ServiceGroupId(0),
        page=1,
        page_size=1,
        require_fresh=True,
        max_wait_seconds=1.0,
    )

    waited_seconds = service._wait_for_refresh(
        request=request,
        sg_ids=sg_ids,
        store=store,
        refresh_applied=True,
    )

    assert waited_seconds >= 1.0
    assert sleep_calls["count"] > 0
