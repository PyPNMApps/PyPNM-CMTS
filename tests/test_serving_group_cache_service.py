# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Maurice Garcia

from __future__ import annotations

import pytest

from pypnm_cmts.api.routes.serving_group.schemas import GetServingGroupTopologyRequest
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
def test_require_fresh_returns_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    service = ServingGroupCacheService()
    store = SgwCacheStore()
    sg_id = ServiceGroupId(1)
    _seed_snapshot(store, sg_id, 1_000.0)

    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id])
    set_sgw_startup_success([sg_id], store, manager, 1_000.0)

    request = GetServingGroupTopologyRequest(
        cmts={"serving_group": {"id": [int(sg_id)]}},
        refresh="heavy",
        require_fresh=True,
        max_wait_seconds=5.0,
    )

    waited_seconds = service._wait_for_refresh(
        request=request,
        sg_ids=[sg_id],
        store=store,
        refresh_applied=True,
    )

    assert waited_seconds == 0.0


@pytest.mark.unit
def test_require_fresh_returns_immediately_when_snapshot_does_not_advance(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_sgw_runtime_state()
    service = ServingGroupCacheService()
    store = SgwCacheStore()
    sg_id = ServiceGroupId(1)
    _seed_snapshot(store, sg_id, 1_000.0)

    settings = CmtsOrchestratorSettings.model_validate(
        {"adapter": {"hostname": "cmts.example", "community": "public"}}
    )
    manager = SgwManager(settings=settings, store=store, service_groups=[sg_id])
    set_sgw_startup_success([sg_id], store, manager, 1_000.0)

    request = GetServingGroupTopologyRequest(
        cmts={"serving_group": {"id": [int(sg_id)]}},
        refresh="heavy",
        require_fresh=True,
        max_wait_seconds=1.0,
    )

    waited_seconds = service._wait_for_refresh(
        request=request,
        sg_ids=[sg_id],
        store=store,
        refresh_applied=True,
    )

    assert waited_seconds == 0.0
